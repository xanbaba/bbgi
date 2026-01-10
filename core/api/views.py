from rest_framework.views import APIView
from rest_framework.response import Response

from core.api.helper import convert_data, parse_time
from core.api.serializers import CustomerAllExportSerializer, CustomerAllSerializer, CustomerSerializer, StatisticExportSerializer, StatisticSerializer, TransactionDataSerializer, VisitExportSerializer, VisitSerializer
from ..mrz_input import get_id_data
from requests.auth import HTTPBasicAuth
import requests
import xmltodict
import xml.etree.ElementTree as ET
import json
import pandas as pd
from datetime import datetime
from tempfile import NamedTemporaryFile
from django.core.files.storage import default_storage
import os
from django.conf import settings
from rest_framework import status
import time
from bbgi.connection import get_connection as g_connection
import psycopg2
from rest_framework.exceptions import ValidationError
from django.http import HttpResponse, FileResponse
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, CreateDisposition, ImpersonationLevel, ShareAccess, CreateOptions, FilePipePrinterAccessMask
from smbprotocol.file_info import InfoType
import io
import uuid
import logging

logger = logging.getLogger(__name__)

def get_connection():
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )

    cursor = conn.cursor()
    return cursor

auth = HTTPBasicAuth(settings.QMATIC_AUTH_USER, settings.QMATIC_AUTH_PASSWORD)


class PassportAPI(APIView):

    def post(self,request):
        from datetime import datetime
        try:
            all_json = json.loads(request.body)
            visit_id = all_json.get("visit_id")
            passport = all_json.get("passport")
            branch_id = all_json.get("branch_id")
            port = all_json.get("port")
            host = all_json.get("host")

            fin = all_json.get("fin",None)
            birth_date = all_json.get("birth_date",None)

            if not fin and not birth_date:
                pass_data = get_id_data(passport)
                fin = pass_data.optional_data
                birth_date = pass_data.birth_date

            date_obj = datetime.strptime(birth_date, "%y%m%d")

            # Adjust the year if it's in the future (Python assumes 00-68 as 2000-2068)
            if date_obj.year > datetime.now().year:
                date_obj = date_obj.replace(year=date_obj.year - 100)

            # Convert to the desired format (YYYY-MM-DD)
            birth_date = date_obj.strftime("%Y-%m-%d")
            
            # Development mode: Use post_xml if USE_POST_XML is True
            if settings.USE_POST_XML:
                name, surname, father_name, image = post_xml(fin)
            else:
                name, surname, father_name, image = get_customer_info(fin, birth_date)
            
            # qmatic progress
            data = {
                'host':host,
                'port':port,
                'branch_id':branch_id,
                'visit_id':visit_id,
                'name':name,
                'surname':surname,
                'father_name':father_name,
                'image':image,
                'fin':fin,
                'birth_date':birth_date
            }
            return Response({"data": data})
        except Exception as e:
            print('xeta vaar,',e)




def call_qmatic(host,port,branch_id,visit_id,first_name,last_name,father_name,photo,fin, birth_date):
    if port == "443":
        url = f"https://{host}/rest/servicepoint/branches/{branch_id}/visits/{visit_id}/parameters/"
    else:
        url = f"http://{host}:{port}/rest/servicepoint/branches/{branch_id}/visits/{visit_id}/parameters/"


    payload = json.dumps({
    "custom1": f"'first_name':'{first_name}','last_name':'{last_name}','father_name':'{father_name}','fin_code':'{fin}','birth_date':'{birth_date}'",
    "photo": photo
    })
    headers = {
    'Content-Type': 'application/json',
    }

    response = requests.request("PUT", url, headers=headers,auth=auth, data=payload)

    print(response.text)



def get_customer_info(fin, birth_date):
    import requests
    url = "http://192.168.253.10:81/HospitalService.asmx"
    try:
        payload = f"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\n  <soap:Body>\n    <GetPersonByPinAndBirthdate xmlns=\"http://tempuri.org/\">\n      <auth>\n        <userName>CustomsHospital</userName>\n        <password>CsHp!@#321Qwer</password>\n      </auth>\n      <pin>{fin}</pin>\n      <birthDate>{birth_date}</birthDate>\n    </GetPersonByPinAndBirthdate>\n  </soap:Body>\n</soap:Envelope>\n"
        headers = {
        'SOAPAction': 'http://tempuri.org/GetPersonByPinAndBirthdate',
        'Content-Type': 'text/xml; charset=utf-8'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response_data = response.text
        response_data = response_data.strip()
        # Parse the XML
        root = ET.fromstring(response_data)

        # Define namespaces
        namespace = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "ns": "http://tempuri.org/"}
        # Extract person fields
        person = root.find(".//ns:person", namespace)
        if person is not None:
            name = person.find("ns:Name", namespace).text
            surname = person.find("ns:Surname", namespace).text
            father_name = person.find("ns:FatherName", namespace).text
            birthdate = person.find("ns:Birthdate", namespace).text
            document_number = person.find("ns:documentNumber", namespace).text
            sex = person.find("ns:sex", namespace).text
            imageStream = person.find("ns:imageStream", namespace).text
            return name, surname, father_name, imageStream
        
        else:
            raise ValidationError({'detail': 'Person not found'})
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def post_xml(fin):
    """
    Parses the given XML response data and extracts required fields.
    Strips any leading or trailing whitespace to prevent parsing errors.
    """
    try:
        response_data = """
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <GetPersonByPinAndBirthdateResponse xmlns="http://tempuri.org/">
                        <GetPersonByPinAndBirthdateResult>
                            <person>
                                <Name>ABAS</Name>
                                <Surname>CƏFƏROV</Surname>
                                <FatherName>FƏRAMƏZ OĞLU ( G/E- DGK),</FatherName>
                                <Birthdate>12.08.1992</Birthdate>
                                <documentNumber>AA4195783</documentNumber>
                                <sex>Kişi</sex>
                                <imageStream>/9j/4AAQSkZJRgABAQEB/AH8AAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJA//Z</imageStream>
                            </person>
                            <StatusCode>1</StatusCode>
                            <StatusDescryption>Success</StatusDescryption>
                        </GetPersonByPinAndBirthdateResult>
                    </GetPersonByPinAndBirthdateResponse>
                </soap:Body>
            </soap:Envelope>
        """
        response_data = response_data.strip()
        
        # Parse the XML
        root = ET.fromstring(response_data)
        
        # Define namespaces
        namespace = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "ns": "http://tempuri.org/"}

        # Extract person fields
        person = root.find(".//ns:person", namespace)
        if person is not None:
            name = person.find("ns:Name", namespace).text
            surname = person.find("ns:Surname", namespace).text
            father_name = person.find("ns:FatherName", namespace).text
            birthdate = person.find("ns:Birthdate", namespace).text
            document_number = person.find("ns:documentNumber", namespace).text
            sex = person.find("ns:sex", namespace).text
            imageStream = person.find("ns:imageStream", namespace).text
            
            return name, surname, father_name, imageStream
        else:
            raise ValueError("Person data not found in the XML.")
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

class MainReport(APIView):

    def multi_filter(self,lst):
        new_lst = [f"'{s}'" for s in lst]
        return new_lst


    def get(self, request):
        try:
            cursor = get_connection()

            min_date_selected = request.GET.get('minDateSelected',None)
            max_date_selected = request.GET.get('maxDateSelected',None)
            call_min_date_selected = request.GET.get('callMinDateSelected',None)
            call_max_date_selected = request.GET.get('callMaxDateSelected',None)
            finish_min_date_selected = request.GET.get('finishMinDateSelected',None)
            finish_max_date_selected = request.GET.get('finishMaxDateSelected',None)
            wait_min_date_selected = request.GET.get('waitMinDateSelected',None)
            wait_max_date_selected = request.GET.get('waitMaxDateSelected',None)
            transac_min_date_selected = request.GET.get('transacMinDateSelected',None)
            transac_max_date_selected = request.GET.get('transacMaxDateSelected',None)
            selected_branches = request.query_params.getlist('selectedBranches',None)
            selected_services = request.query_params.getlist('selectedServices',None)
            selected_first_name = request.GET.get('first_name')
            selected_last_name = request.GET.get('last_name')
            selected_father_name = request.GET.get('father_name')
            selected_birth_date = request.query_params.getlist('birth_date')
            status = request.query_params.getlist('status')
            pin = request.GET.get('pin')
            ticket_id = request.GET.get('ticket_id')
            staff_name = request.GET.get('staff_name')

            entered_text = request.query_params.get('enteredText')
            pg_size = request.query_params.get('pg_size', 10)
            pg_num = request.query_params.get('pg_num', 1)

            query = """
                select fvt.date_key, fvt.create_timestamp, db."name" as branch_name, db.id as branch_id,
                ds.id as service_id, dv.ticket_id, ds."name" as service_name,
                fvt.waiting_time, fvt.call_timestamp ,fvt.transaction_time,
                fvt.time_key+fvt.time_seconds as created_time, 
                dc.first_name, dc.last_name, dc.pin , dc.father_name , dc.birth_date, dv.custom_2  as result, 

                fvt.outcome_key,dsf.first_name as staff_first_name,dsf.last_name as staff_last_name, dsf.name as staff_name
                from stat.fact_visit_transaction fvt 
                left join stat.dim_visit dv on dv.id = fvt.visit_key 
                left join stat.dim_branch db on db.id = fvt.branch_key 
                left join stat.dim_service ds on ds.id = fvt.service_key 
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                left join stat.dim_staff dsf on dsf.id = fvt.staff_key 
                where 1=1
            """

            count_query = """
                select count(fvt.id)
                from stat.fact_visit_transaction fvt 
                left join stat.dim_visit dv on dv.id = fvt.visit_key 
                left join stat.dim_branch db on db.id = fvt.branch_key 
                left join stat.dim_service ds on ds.id = fvt.service_key 
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                left join stat.dim_staff dsf on dsf.id = fvt.staff_key 
                where 1=1

            """


            if min_date_selected and max_date_selected:
                query += f"AND fvt.create_timestamp >= '{min_date_selected} 00:00:00' AND fvt.create_timestamp <= '{max_date_selected} 23:59:59'"
                count_query += f"AND fvt.create_timestamp >= '{min_date_selected} 00:00:00' AND fvt.create_timestamp <= '{max_date_selected} 23:59:59'"


            if call_min_date_selected and call_max_date_selected:
                query += f"AND fvt.call_timestamp >= '{call_min_date_selected} 00:00:00' AND fvt.call_timestamp <= '{call_max_date_selected} 23:59:59'"
                count_query += f"AND fvt.call_timestamp >= '{call_min_date_selected} 00:00:00' AND fvt.call_timestamp <= '{call_max_date_selected} 23:59:59'"

            if finish_min_date_selected and finish_max_date_selected:
                query += f"AND (fvt.call_timestamp + (fvt.transaction_time * INTERVAL '1 second')) >= '{finish_min_date_selected} 00:00:00' AND (fvt.call_timestamp + (fvt.transaction_time * INTERVAL '1 second')) <= '{finish_max_date_selected} 23:59:59'"
                count_query += f"AND (fvt.call_timestamp + (fvt.transaction_time * INTERVAL '1 second')) >= '{finish_min_date_selected} 00:00:00' AND (fvt.call_timestamp + (fvt.transaction_time * INTERVAL '1 second')) <= '{finish_max_date_selected} 23:59:59'"

            if wait_min_date_selected and wait_max_date_selected:
                wait_min_date_selected = parse_time(wait_min_date_selected)
                wait_max_date_selected = parse_time(wait_max_date_selected)

                query += f"AND fvt.waiting_time BETWEEN '{wait_min_date_selected}' AND '{wait_max_date_selected}'"
                count_query += f"AND fvt.waiting_time BETWEEN '{wait_min_date_selected}'AND '{wait_max_date_selected}'"

            if transac_min_date_selected and transac_max_date_selected:
                transac_min_date_selected = parse_time(transac_min_date_selected)
                transac_max_date_selected = parse_time(transac_max_date_selected)

                query += f"AND fvt.transaction_time BETWEEN '{transac_min_date_selected}' AND '{transac_max_date_selected}'"
                count_query += f"AND fvt.transaction_time BETWEEN '{transac_min_date_selected}'AND '{transac_max_date_selected}'"
            
            if status:
                lst = self.multi_filter(status)
                query += f"AND dv.custom_2 IN ({','.join(lst)}) "
                count_query += f"AND dv.custom_2 IN ({','.join(lst)}) "

            if selected_branches and not selected_branches == ['']:
                query += f"AND db.id in ({','.join(selected_branches)}) "
                count_query += f"AND db.id IN ({','.join(selected_branches)}) "


            if selected_services and not selected_services == ['']:
                query += f"AND ds.origin_id IN ({','.join(selected_services)}) "
                count_query += f"AND ds.origin_id IN ({','.join(selected_services)}) "


            if selected_first_name:
                query += f"AND dc.first_name ilike '%{selected_first_name}%'"
                count_query += f"AND dc.first_name ilike '%{selected_first_name}%'"

            if ticket_id:
                query += f"AND dv.ticket_id ilike '%{ticket_id}%'"
                count_query += f"AND dv.ticket_id ilike '%{ticket_id}%'"

            if selected_father_name:
                query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                count_query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                

            if selected_last_name:
                query += f"AND dc.last_name ilike '%{selected_last_name}%'"
                count_query += f"AND dc.last_name ilike '%{selected_last_name}%'"

            if selected_birth_date:
                lst = self.multi_filter(selected_birth_date)
                query += f"AND dc.birth_date IN ({','.join(lst)}) "
                count_query += f"AND dc.birth_date IN ({','.join(lst)}) "

            if pin:
                query += f"AND dc.pin ilike '%{pin}%'"
                count_query += f"AND dc.pin ilike '%{pin}%'"

            if staff_name:
                query += f"AND dsf.name ilike '%{staff_name}%'"
                count_query += f"AND dsf.name ilike '%{staff_name}%'"


            if entered_text:
                query += f"""
                    AND (
                        dc.first_name ilike '%{entered_text}%' OR 
                        dc.father_name ilike '%{entered_text}%' OR 
                        dc.last_name ilike '%{entered_text}%' OR
                        dc.pin ilike '%{entered_text}%'
                    )
                """

                count_query += f"""
                    AND (
                        dc.first_name ilike '%{entered_text}%' OR 
                        dc.father_name ilike '%{entered_text}%' OR 
                        dc.last_name ilike '%{entered_text}%' OR
                        dc.pin ilike '%{entered_text}%'
                    )
                """


            query += f"order by fvt.create_timestamp DESC OFFSET {pg_size} * ({pg_num} - 1) LIMIT {pg_size};"
            count_query +=";"
            cursor.execute(query)
            data = convert_data(cursor)
            cursor.execute(count_query)
            count = cursor.fetchall()



            extract_integer = lambda x: x[0] if isinstance(x, tuple) else x
            count = extract_integer(count[0])
            cursor.close()
            result = StatisticSerializer(data,many = True).data

            return Response({"data":result,"count":count})
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class CustomerList(APIView):

    def get(self, request):
        cursor = get_connection()
        
        selected_branches = request.query_params.getlist('selectedBranches')
        entered_text = request.query_params.get('enteredText')
        customer_id = request.query_params.get('customer_id')
        min_created_at = request.GET.get('minCreatedAtSelected')
        max_created_at = request.GET.get('maxCreatedAtSelected')
        order_created_at = request.GET.get('orderCreatedAt')
        selected_first_name = request.GET.get('first_name')
        selected_last_name = request.GET.get('last_name')
        selected_father_name = request.GET.get('father_name')
        pin = request.GET.get('pin')
        customs_number = request.GET.get('customsnumber')
        name = request.GET.get('name')
        min_date_selected = request.GET.get('minDateSelected',None)
        max_date_selected = request.GET.get('maxDateSelected',None)
        pg_size = request.query_params.get('pg_size', 10)
        pg_num = request.query_params.get('pg_num', 1)

        query = """
            select dc.first_name, dc.last_name, dc.father_name, dc.birth_date, dc.pin, dc.phone, dc.visits_count  as visits, dc.id as customer_id,dc.created_at,
            COALESCE(vrf.is_risk, false) as is_risk, vrf.note as note
            from stat.dim_visit dv 
            left join stat.dim_customer dc on dc.id::varchar = dv.custom_1 
            left join stat.fact_visit_transaction  fvt on fvt.visit_key = dv.id 
            left join stat.dim_branch db on db.id = fvt.branch_key
            left join visits_risk_fin vrf on vrf.fin = dc.pin
            where dc.id is not null
        
        """
        count_query = """
            SELECT COUNT(*) AS sum
            FROM (
                SELECT dc.first_name, dc.last_name, dc.pin
                FROM stat.dim_visit dv 
                LEFT JOIN stat.dim_customer dc ON dc.id::varchar = dv.custom_1 
                LEFT JOIN stat.fact_visit_transaction  fvt on fvt.visit_key = dv.id 
                LEFT JOIN stat.dim_branch db ON db.id = fvt.branch_key
                where dc.id is not null
        """

        if selected_first_name:
                query += f"AND dc.first_name ilike '%{selected_first_name}%'"
                count_query += f"AND dc.first_name ilike '%{selected_first_name}%'"

        if selected_last_name:
                query += f"AND dc.last_name ilike '%{selected_last_name}%'"
                count_query += f"AND dc.last_name ilike '%{selected_last_name}%'"

        if selected_father_name:
                query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                count_query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                
        if customer_id:
            query += f"and dc.id = {customer_id} "
            count_query += f"and dc.id = {customer_id} "

        if selected_branches:
            query += f"AND db.id in ({','.join(selected_branches)}) "
            count_query += f"AND db.id IN ({','.join(selected_branches)}) "

        if entered_text:
            query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%')) "
            count_query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%'))"

        if pin:
            query += f"AND dc.pin ilike '%{pin}%'"
            count_query += f"AND dc.pin ilike '%{pin}%'"

        if name:
            query += f"AND ds.name ilike '%{name}%'"
            count_query += f"AND ds.name ilike '%{name}%'"

        if customs_number:
            customs_filter = f"""AND EXISTS (
                SELECT 1 
                FROM visits_declaration vd 
                WHERE vd.visit_id = dv.origin_id::varchar 
                AND vd.customs_number ILIKE '%{customs_number}%'
            )"""
            query += customs_filter
            count_query += customs_filter


        if min_date_selected and max_date_selected:
            query += f"AND dc.birth_date >= '{min_date_selected}' AND dc.birth_date <= '{max_date_selected}'"
            count_query += f"AND dc.birth_date >= '{min_date_selected}' AND dc.birth_date <= '{max_date_selected}'"

        if min_created_at and max_created_at:
            query += f"AND dc.created_at >= '{min_created_at} 00:00:00' AND dc.created_at <= '{max_created_at} 23:59:59'"
            count_query += f"AND dc.created_at >= '{min_created_at} 00:00:00' AND dc.created_at <= '{max_created_at} 23:59:59'"
        
        order = "asc"
        if order_created_at == 'asc' or order_created_at == 'desc':
            order = order_created_at
            
        query += f"group by custom_1,dc.first_name,dc.last_name, dc.father_name, dc.birth_date,dc.pin, dc.phone, dc.visits_count, dc.id,dc.created_at, vrf.is_risk, vrf.note order by dc.created_at {order} OFFSET {pg_size} * ({pg_num} - 1) LIMIT {pg_size};"

        cursor.execute(query)
        data = convert_data(cursor)
        result = CustomerAllSerializer(data,many = True).data
        
       
        count_query +=  """
                GROUP BY custom_1, dc.first_name, dc.last_name, dc.father_name, dc.birth_date,dc.pin, dc.visits_count, dc.id,dc.created_at
                ORDER BY dc.first_name
            ) AS subquery
            ;  
            """


        cursor.execute(count_query)
        count = cursor.fetchall()
    

        extract_integer = lambda x: x[0] if isinstance(x, tuple) else x
        all = {"data": result ,"count":extract_integer(count[0])}
        cursor.close()

        return Response(all)




class VisitListOfCustomer(APIView):

    def get(self,request):
        min_date_selected = request.query_params.get('minDateSelected')
        max_date_selected = request.query_params.get('maxDateSelected')
        selected_customer = request.query_params.get('customer_id')
        selected_branches = request.query_params.getlist('selectedBranches')
        selected_services = request.query_params.getlist('selectedServices')
        selected_first_name = request.GET.get('first_name')
        selected_last_name = request.GET.get('last_name')
        selected_father_name = request.GET.get('father_name')
        entered_text = request.query_params.get('enteredText')


        # Get customer profile with phone, birth_date and image from visits_visit
        profile_query = f"""
            SELECT 
                dc.first_name, 
                dc.last_name, 
                dc.pin, 
                dc.father_name,
                (SELECT vv.birth_date FROM visits_visit vv 
                 WHERE vv.visit_id IN (
                     SELECT dv.origin_id::varchar FROM dim_visit dv 
                     WHERE dv.custom_1 = '{selected_customer}' 
                     ORDER BY dv.created_timestamp DESC LIMIT 1
                 ) ORDER BY vv.id LIMIT 1) as birth_date_from_visit,
                dc.birth_date,
                COALESCE(
                    (SELECT vv.phone FROM visits_visit vv 
                     WHERE vv.visit_id IN (
                         SELECT dv.origin_id::varchar FROM dim_visit dv 
                         WHERE dv.custom_1 = '{selected_customer}' 
                         ORDER BY dv.created_timestamp DESC LIMIT 1
                     ) ORDER BY vv.id LIMIT 1),
                    dc.phone
                ) as phone,
                (SELECT vv.image FROM visits_visit vv 
                 WHERE vv.visit_id IN (
                     SELECT dv.origin_id::varchar FROM dim_visit dv 
                     WHERE dv.custom_1 = '{selected_customer}' 
                     ORDER BY dv.created_timestamp DESC LIMIT 1
                 ) ORDER BY vv.id LIMIT 1) as image
            FROM stat.dim_customer AS dc
            WHERE dc.id = %s
        """
        cursor = get_connection()
        cursor.execute(profile_query, (selected_customer,))
        columns = [col[0] for col in cursor.description]
        profile_dic_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not profile_dic_data:
            return Response({"customer_id":"Customer not found!"},status=status.HTTP_404_NOT_FOUND)
        
        # Use birth_date from visits_visit if available, otherwise from dim_customer
        profile_data = profile_dic_data[0]
        if profile_data.get('birth_date_from_visit'):
            profile_data['birth_date'] = profile_data['birth_date_from_visit']
        # Remove the temporary field
        profile_data.pop('birth_date_from_visit', None)
        
        profile_serializer_data = CustomerSerializer(profile_data).data
        pg_size = request.query_params.get('pg_size', 10)
        pg_num = request.query_params.get('pg_num', 1)

        query = f"""
                SELECT 
                    dv.id AS visit_key,
                    dv.origin_id AS visit_origin_id,
                    COUNT(fvt.id) AS transactions_count,
                    dc.first_name, dc.last_name, dc.pin,
                dv.ticket_id,
                dv.created_timestamp,
                sum(fvt.transaction_time) as total_transaction_time, 
                    sum(fvt.waiting_time) as total_wait_time,
                (SELECT s_ds.name FROM fact_visit_transaction s_fvt
                INNER JOIN dim_service AS s_ds ON s_ds.id = s_fvt.service_key
                WHERE s_fvt.visit_key = dv.id
                    ORDER BY create_timestamp LIMIT 1) 
                    AS service_name,
                (SELECT vn.status FROM visits_note vn
                WHERE vn.visit_id = dv.id::varchar 
                    AND vn.action = 'finish'
                    ORDER BY vn.created_at ASC LIMIT 1) 
                    AS result,
                (SELECT dvet.name FROM fact_visit_transaction s_fvt
                LEFT JOIN fact_visit_events s_fve ON s_fve.visit_transaction_id = s_fvt.id
                LEFT JOIN dim_visit_event_type dvet ON dvet.id = s_fve.visit_event_type_key
                WHERE s_fvt.visit_key = dv.id
                    ORDER BY s_fvt.create_timestamp DESC LIMIT 1) 
                    AS status
                FROM 
                    dim_visit dv
                left join fact_visit_transaction fvt ON dv.id = fvt.visit_key
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                where dv.custom_1 is not null

        """

        count_query = """
                SELECT COUNT(*) AS sum from (		
                SELECT
                    dv.id AS visit_key,
                    COUNT(fvt.id) AS transactions_count,
                    dc.first_name, dc.last_name, dc.pin, 
                dv.ticket_id,
                dv.created_timestamp,
                sum(fvt.transaction_time) as total_transaction_time, 
                    sum(fvt.waiting_time) as total_wait_time,
                (SELECT s_ds.name FROM fact_visit_transaction s_fvt
                INNER JOIN dim_service AS s_ds ON s_ds.id = s_fvt.service_key
                WHERE s_fvt.visit_key = dv.id
                    ORDER BY create_timestamp LIMIT 1) 
                    AS service_name
                FROM 
                    dim_visit dv
                left join fact_visit_transaction fvt ON dv.id = fvt.visit_key
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                where dv.custom_1 is not null

        """

        if min_date_selected and max_date_selected:
            query += f"AND fvt.date_key BETWEEN '{min_date_selected}' AND '{max_date_selected}'"
            count_query += f"AND fvt.date_key BETWEEN '{min_date_selected}' AND '{max_date_selected}'"

        if selected_branches:
            query += f"AND db.id in ({','.join(selected_branches)}) "
            count_query += f"AND db.id IN ({','.join(selected_branches)}) "

        if selected_services and not selected_services == ['']:

            query += f"""and dv.id in (SELECT sfvt.visit_key FROM fact_visit_transaction sfvt INNER JOIN dim_service AS sds ON sds.id = sfvt.service_key WHERE sds.origin_id in ({','.join(selected_services)}))"""
            count_query += f"and dv.id in (SELECT sfvt.visit_key FROM fact_visit_transaction sfvt INNER JOIN dim_service AS sds ON sds.id = sfvt.service_key WHERE sds.origin_id in ({','.join(selected_services)})) "

        if selected_customer:
            query += f"and dc.id = {selected_customer} "
            count_query += f"and dc.id = {selected_customer} "

        if selected_first_name:
                query += f"AND dc.first_name ilike '%{selected_first_name}%'"
                count_query += f"AND dc.first_name ilike '%{selected_first_name}%'"

        if selected_last_name:
                query += f"AND dc.last_name ilike '%{selected_last_name}%'"
                count_query += f"AND dc.last_name ilike '%{selected_last_name}%'"

        if selected_father_name:
                query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                count_query += f"AND dc.father_name ilike '%{selected_father_name}%'"

        if entered_text:
                query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%'))"
                count_query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%'))"

        query += f'GROUP BY dv.id, dv.origin_id, dc.first_name, dc.last_name, dc.pin, dv.ticket_id OFFSET {pg_size} * ({pg_num} - 1) LIMIT {pg_size}'
        

        count_query+='GROUP BY dv.id,dc.first_name, dc.last_name, dc.pin, dv.ticket_id)  as subquery;'
        
        cursor = get_connection()
        cursor.execute(query)
        data = convert_data(cursor)
        
        # Get all origin_ids from the result (visits_declaration.visit_id = dim_visit.origin_id)
        origin_ids = [str(item['visit_origin_id']) for item in data if item.get('visit_origin_id')]
        
        # Fetch declarations for all visits using origin_id
        declarations_map = {}
        if origin_ids:
            # Use parameterized query to prevent SQL injection
            placeholders = ','.join(['%s'] * len(origin_ids))
            declarations_query = f"""
                SELECT 
                    visit_id,
                    id,
                    user_id,
                    type,
                    customs_number,
                    representative_voen,
                    representative_name,
                    company_voen,
                    company_name,
                    created_at
                FROM visits_declaration
                WHERE visit_id IN ({placeholders})
                ORDER BY visit_id, created_at DESC
            """
            cursor.execute(declarations_query, origin_ids)
            declarations_data = convert_data(cursor)
            
            # Group declarations by visit_id (which is origin_id)
            for decl in declarations_data:
                visit_id = str(decl['visit_id'])
                if visit_id not in declarations_map:
                    declarations_map[visit_id] = []
                declarations_map[visit_id].append({
                    'id': decl['id'],
                    'user_id': decl['user_id'],
                    'type': decl['type'],
                    'customs_number': decl['customs_number'],
                    'representative_voen': decl['representative_voen'],
                    'representative_name': decl['representative_name'],
                    'company_voen': decl['company_voen'],
                    'company_name': decl['company_name'],
                    'created_at': decl['created_at'].isoformat() if decl.get('created_at') else None
                })
        
        # Add declarations to each visit data using origin_id
        # Remove phone, birth_date, image from visit data (they should only be in profile)
        for item in data:
            origin_id = str(item.get('visit_origin_id', ''))
            item['declarations'] = declarations_map.get(origin_id, [])
            # Remove these fields from visit data
            item.pop('phone', None)
            item.pop('birth_date', None)
            item.pop('image', None)
        
        result = VisitSerializer(data,many = True).data
        cursor.execute(count_query)
        count = cursor.fetchall()
        


        extract_integer = lambda x: x[0] if isinstance(x, tuple) else x

        all = {"data": result,"count":extract_integer(count[0]),'profile':profile_serializer_data}
        cursor.close()
        return Response(all)

    



class Export(APIView):
    def get(self,request):
        data_url =request.query_params.get('data_url')
        selected_branches = request.query_params.getlist('selectedBranches')
        entered_text = request.query_params.get('enteredText')
        customer_id = request.query_params.get('customer_id')
        min_date_selected = request.query_params.get('minDateSelected')
        max_date_selected = request.query_params.get('maxDateSelected')
        selected_customer = request.query_params.get('customer_id')
        selected_services = request.query_params.getlist('selectedServices')
        status = request.query_params.getlist('status')
        selected_visit = request.query_params.get('visit')
        selected_first_name = request.GET.get('first_name')
        selected_last_name = request.GET.get('last_name')
        selected_father_name = request.GET.get('father_name')


        cursor = get_connection()
        if data_url=="report":
            call_min_date_selected = request.GET.get('callMinDateSelected',None)
            call_max_date_selected = request.GET.get('callMaxDateSelected',None)
            finish_min_date_selected = request.GET.get('finishMinDateSelected',None)
            finish_max_date_selected = request.GET.get('finishMaxDateSelected',None)
            wait_min_date_selected = request.GET.get('waitMinDateSelected',None)
            wait_max_date_selected = request.GET.get('waitMaxDateSelected',None)
            transac_min_date_selected = request.GET.get('transacMinDateSelected',None)
            transac_max_date_selected = request.GET.get('transacMaxDateSelected',None)
            selected_birth_date = request.query_params.getlist('birth_date')
            pin = request.GET.get('pin')
            ticket_id = request.GET.get('ticket_id')
            staff_name = request.GET.get('staff_name')

            query = """
                select fvt.date_key, fvt.create_timestamp, db."name" as branch_name, db.id as branch_id,
                ds.id as service_id, dv.ticket_id, ds."name" as service_name,
                fvt.waiting_time, fvt.call_timestamp ,fvt.transaction_time,
                fvt.time_key+fvt.time_seconds as created_time, 
                dc.first_name, dc.last_name, dc.pin , dc.father_name , dc.birth_date,
                fvt.outcome_key,dsf.first_name as staff_first_name,dsf.last_name as staff_last_name, dsf.name as staff_name
                from stat.fact_visit_transaction fvt 
                left join stat.dim_visit dv on dv.id = fvt.visit_key 
                left join stat.dim_branch db on db.id = fvt.branch_key 
                left join stat.dim_service ds on ds.id = fvt.service_key 
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                left join stat.dim_staff dsf on dsf.id = fvt.staff_key 
                where 1=1
                """
            
            if min_date_selected and max_date_selected:
                query += f"AND fvt.create_timestamp >= '{min_date_selected} 00:00:00' AND fvt.create_timestamp <= '{max_date_selected} 23:59:59'"

            if call_min_date_selected and call_max_date_selected:
                query += f"AND fvt.call_timestamp BETWEEN '{call_min_date_selected}' AND '{call_max_date_selected}'"

            if finish_min_date_selected and finish_max_date_selected:
                query += f"AND fvt.call_timestamp + (fvt.transaction_time * INTERVAL '1 second') BETWEEN '{finish_min_date_selected} 00:00:00' AND '{finish_max_date_selected} 23:59:59'"

            if wait_min_date_selected and wait_max_date_selected:
                wait_min_date_selected = parse_time(wait_min_date_selected)
                wait_max_date_selected = parse_time(wait_max_date_selected)

                query += f"AND fvt.waiting_time BETWEEN '{wait_min_date_selected}' AND '{wait_max_date_selected}'"

            if transac_min_date_selected and transac_max_date_selected:
                transac_min_date_selected = parse_time(transac_min_date_selected)
                transac_max_date_selected = parse_time(transac_max_date_selected)

                query += f"AND fvt.transaction_time BETWEEN '{transac_min_date_selected}' AND '{transac_max_date_selected}'"
            

            if selected_branches and not selected_branches == ['']:
                query += f"AND db.id in ({','.join(selected_branches)}) "


            if selected_services and not selected_services == ['']:
                query += f"AND ds.origin_id IN ({','.join(selected_services)}) "


            if selected_first_name:
                query += f"AND dc.first_name ilike '%{selected_first_name}%'"

            if ticket_id:
                query += f"AND dv.ticket_id ilike '%{ticket_id}%'"

            if selected_father_name:
                query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                

            if selected_last_name:
                query += f"AND dc.last_name ilike '%{selected_last_name}%'"

            if selected_birth_date:
                lst = self.multi_filter(selected_birth_date)
                query += f"AND dc.birth_date IN ({','.join(lst)}) "

            if pin:
                query += f"AND dc.pin ilike '%{pin}%'"

            if staff_name:
                query += f"AND dsf.name ilike '%{staff_name}%'"
                count_query += f"AND dsf.name ilike '%{staff_name}%'"

            if entered_text:
                query += f"""
                    AND (
                        dc.first_name ilike '%{entered_text}%' OR 
                        dc.father_name ilike '%{entered_text}%' OR 
                        dc.last_name ilike '%{entered_text}%' OR
                        dc.pin ilike '%{entered_text}%'
                    )
                """



            query += f"order by fvt.create_timestamp DESC;"
            cursor.execute(query)
            data = convert_data(cursor)
            cursor.close()
            result = StatisticExportSerializer(data,many = True).data

            
        elif data_url=="customer-list":
            query = """
            select dc.first_name, dc.last_name, dc.father_name, dc.birth_date, dc.pin, dc.visits_count  as visits, dc.id as customer_id,dc.created_at
            from stat.dim_visit dv 
            left join stat.dim_customer dc on dc.id::varchar = dv.custom_1 
            left join stat.fact_visit_transaction  fvt on fvt.visit_key = dv.id 
            left join stat.dim_branch db on db.id = fvt.branch_key
            where dv.custom_1 is not null and dc.id is not null
                """

            pin = request.GET.get('pin')
            name = request.GET.get('name')
            min_created_at = request.GET.get('minCreatedAtSelected')
            max_created_at = request.GET.get('maxCreatedAtSelected')
            if selected_first_name:
                    query += f"AND dc.first_name ilike '%{selected_first_name}%'"

            if selected_last_name:
                    query += f"AND dc.last_name ilike '%{selected_last_name}%'"

            if selected_father_name:
                    query += f"AND dc.father_name ilike '%{selected_father_name}%'"
                    
            if customer_id:
                query += f"and dc.id = {customer_id} "

            if selected_branches:
                query += f"AND db.id in ({','.join(selected_branches)}) "

            if entered_text:
                query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%')) "

            if pin:
                query += f"AND dc.pin ilike '%{pin}%'"

            if name:
                query += f"AND ds.name ilike '%{name}%'"

            if min_date_selected and max_date_selected:
                query += f"AND dc.birth_date BETWEEN '{min_date_selected}' AND '{max_date_selected}'"

            if min_created_at and max_created_at:
                query += f"AND dc.created_at >= '{min_created_at} 00:00:00' AND dc.created_at <= '{max_created_at} 23:59:59'"

            query += f" group by custom_1,dc.first_name,dc.last_name, dc.father_name, dc.birth_date,dc.pin, dc.visits_count,dc.created_at, dc.id order by dc.first_name;"

            cursor.execute(query)
            data = convert_data(cursor)
            result = CustomerAllExportSerializer(data,many = True).data

        elif data_url == "visit-list-customer":
            query = f"""
                SELECT 
                    dv.id AS visit_key,
                    COUNT(fvt.id) AS transactions_count,
                    dc.first_name, dc.last_name, dc.pin, 
                dv.ticket_id,
                dv.created_timestamp,
                sum(fvt.transaction_time) as total_transaction_time, 
                    sum(fvt.waiting_time) as total_wait_time,
                (SELECT s_ds.name FROM fact_visit_transaction s_fvt
                INNER JOIN dim_service AS s_ds ON s_ds.id = s_fvt.service_key
                WHERE s_fvt.visit_key = dv.id
                    ORDER BY create_timestamp LIMIT 1) 
                    AS service_name
                FROM 
                    dim_visit dv
                left join fact_visit_transaction fvt ON dv.id = fvt.visit_key
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                where dv.custom_1 is not null

            """
            if min_date_selected and max_date_selected:
                query += f"AND fvt.date_key BETWEEN {min_date_selected} AND {max_date_selected} "

            if selected_branches:
                query += f"AND db.id in ({','.join(selected_branches)}) "

            if selected_services and not selected_services == ['']:
                query += f"""and dv.id in (SELECT sfvt.visit_key FROM fact_visit_transaction sfvt INNER JOIN dim_service AS sds ON sds.id = sfvt.service_key WHERE sds.origin_id in ({','.join(selected_services)}))"""

            if selected_customer:
                query += f"and dc.id = {selected_customer} "

            if selected_first_name:
                    query += f"AND dc.first_name ilike '%{selected_first_name}%'"

            if selected_last_name:
                    query += f"AND dc.last_name ilike '%{selected_last_name}%'"

            if selected_father_name:
                    query += f"AND dc.father_name ilike '%{selected_father_name}%'"

            if entered_text:
                    query += f"and (lower(dc.first_name) like lower('%{entered_text}%') or lower(dc.last_name) like lower('%{entered_text}%') or lower(dc.pin) like lower('%{entered_text}%'))"

            query += f'GROUP BY dv.id,dc.first_name, dc.last_name, dc.pin, dv.ticket_id'
        
            cursor = get_connection()
            cursor.execute(query)
            data = convert_data(cursor)
            result = VisitExportSerializer(data,many = True).data

        elif data_url == "visit-transaction":
            if not selected_visit:
                return Response({'visit_id':'visit id required'})
            query = f"""
        
                select 
                fvt.time_key + fvt.time_seconds + fvt.waiting_time  as call_time,  
                fvt.waiting_time,
                fvt.time_key + fvt.time_seconds + fvt.waiting_time + fvt.transaction_time as finish_time,
                fvt.transaction_time,
                dvo."name" as visit_outcome, ds.first_name as user_first_name, ds.last_name as user_last_name, ds."name" as user_login
                from stat.fact_visit_transaction fvt 
                left join stat.dim_visit_outcome dvo on dvo.id = fvt.visit_outcome_key 
                left join stat.dim_staff ds on ds.id = fvt.staff_key
                left join stat.dim_visit dv on dv.id = fvt.visit_key
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1 
                where fvt.visit_key = {selected_visit}
                order by fvt.time_key, fvt.time_seconds 
                ;
            
            """

            cursor.execute(query)
            data = cursor.fetchall()

            
            
            # Function to convert seconds to H:M:S format
            def format_time(total_seconds):
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

            # Format the time columns in the result
            result = []
            for row in data:
                formatted_row = {
                    "Call Time": format_time(row[0]),
                    "Waiting Time": format_time(row[1]),
                    "Finish Time": format_time(row[2]),
                    "Transaction Time": format_time(row[3]),
                    "Outcome": row[4],
                    "User First n.": row[5],
                    "User Last n.": row[6],
                    "User Login": row[7]
                }
                result.append(formatted_row)
            


        url = self.export_data(result,'excel',request.get_host())
        return Response({"url":url})

    def export_data(self, data, key, host):
        df = pd.DataFrame(data)
        df.index.name = '#'
        df.index = df.index + 1
        print(df)
        now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        if not os.path.exists('media'):
            os.makedirs('media')
        url = ''
        if not isinstance(df, pd.DataFrame):
            df = df.to_frame()
        
        df.memory_usage(deep=True)
        link = f"output-{now}."

        if key == 'excel':
            url = self.generate_url('xlsx', link, df)
        elif key == 'csv':
            url = self.generate_url('csv', link, df)

        url = 'http://' + host + '/stmedia/' + url
        return url
    


    def generate_url(self,extention,link,df,html=None):
        # import openpyxl

        name = link+extention
        with NamedTemporaryFile(mode='w+b', delete=False) as tmp:
            print(df)
            path = os.path.join(settings.BASE_DIR,'media',name)
            
            print("DFIN USDUUUDSUDSUDSUDSUDSUDUS")
            
            if extention=='csv':
                df.to_csv(path, index=False)
            elif extention=='xlsx':
                writer = pd.ExcelWriter(path=path, engine='xlsxwriter') 
                df.to_excel(writer)
                writer.save()
                # df.to_excel(path, index=False)


            tmp.seek(0)


        ds = default_storage
        # file_name = ds.save(name, open(tmp.name, 'rb'))

        if os.path.isfile(tmp.name):
            os.remove(tmp.name)
        # url = ds.url(file_name)
        return name
    

class TransactionList(APIView):

    def get(self, request,visit_id):
        cursor = get_connection()
        
        pg_size = request.query_params.get('pg_size', 10)
        pg_num = request.query_params.get('pg_num', 1)

        visit_query = f"""
            SELECT 
                dv.id,
                dv.ticket_id,
                dv.created_timestamp,
                dv.custom_1,
                dv.origin_id
            FROM dim_visit AS dv 
            WHERE dv.id = '{visit_id}'
        """    
        cursor.execute(visit_query)
        visit_data = convert_data(cursor)

        if not visit_data:
            return Response({'visit_id':'Visit_id not found!'},status = status.HTTP_404_NOT_FOUND)
        visit_data = visit_data[0]
        customer = visit_data['custom_1']
        visit_origin_id = visit_data.get('origin_id')
        if not customer:
            return Response({'Customer':'Customer not found!'},status = status.HTTP_404_NOT_FOUND)
        
        query = f"""
            SELECT * FROM (
                SELECT DISTINCT ON (fvt.id)
                fvt.id, fvt.create_timestamp, fvt.waiting_time, fvt.call_timestamp ,fvt.transaction_time, fvt.outcome_key,
                ds.first_name,ds.last_name,ds.name,
                vn.content as note,
                vn.status as result,
                vn.table as table,
                dvet.name as status
                from fact_visit_transaction AS fvt
                left join stat.dim_visit dv on dv.id = fvt.visit_key 
                left join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                left join stat.dim_staff ds on ds.id = fvt.staff_key 
                left join visits_note vn on vn.user_id::integer = ds.origin_id AND vn.visit_id = dv.origin_id::varchar
                left join fact_visit_events fve on fve.visit_transaction_id = fvt.id
                left join dim_visit_event_type dvet on dvet.id = fve.visit_event_type_key
                where fvt.visit_key = '{visit_id}'
                ORDER BY fvt.id, vn.created_at DESC
            ) AS subquery
            ORDER BY id
            OFFSET {pg_size} * ({pg_num} - 1) LIMIT {pg_size}
        """
        count_query = f"""
                SELECT COUNT(*) AS sum
                FROM (
                    SELECT 
                        fvt.id
                    FROM fact_visit_transaction AS fvt
                    WHERE fvt.visit_key = {visit_id}
                ) AS subquery;

        """
        
        cursor.execute(query)
        data = convert_data(cursor)
        data = TransactionDataSerializer(data,many = True).data
        cursor.execute(count_query)
        count = cursor.fetchall()
        
        # Get profile data with risk status
        # Use phone, birth_date and image from visits_visit if available, otherwise from dim_customer
        profile_query = f"""
            SELECT 
                dc.first_name, 
                dc.last_name, 
                dc.pin, 
                dc.father_name,
                (SELECT vv.birth_date FROM visits_visit vv WHERE vv.visit_id = '{visit_origin_id}'::varchar ORDER BY vv.id LIMIT 1) as birth_date_from_visit,
                dc.birth_date as birth_date,
                COALESCE(
                    (SELECT vv.phone FROM visits_visit vv WHERE vv.visit_id = '{visit_origin_id}'::varchar ORDER BY vv.id LIMIT 1),
                    dc.phone
                ) as phone,
                (SELECT vv.image FROM visits_visit vv 
                 WHERE vv.visit_id IN (
                     SELECT dv.origin_id::varchar FROM dim_visit dv 
                     WHERE dv.custom_1 = '{customer}' 
                     ORDER BY dv.created_timestamp DESC LIMIT 1
                 ) ORDER BY vv.id LIMIT 1) as image,
                COALESCE(vrf.is_risk, false) as is_risk
            FROM stat.dim_customer AS dc
            LEFT JOIN visits_risk_fin vrf ON vrf.fin = dc.pin
            WHERE dc.id = {customer}
        """
        cursor.execute(profile_query)
        profile_data = convert_data(cursor)[0]
        
        # Use birth_date from visits_visit if available, otherwise from dim_customer
        if profile_data.get('birth_date_from_visit'):
            profile_data['birth_date'] = profile_data['birth_date_from_visit']
        # Remove the temporary field
        profile_data.pop('birth_date_from_visit', None)
        
        # Fetch declarations for the visit using origin_id
        declarations_query = f"""
            SELECT 
                visit_id,
                id,
                user_id,
                type,
                customs_number,
                representative_voen,
                representative_name,
                company_voen,
                company_name,
                created_at
            FROM visits_declaration
            WHERE visit_id = %s
            ORDER BY created_at DESC
        """
        # Use origin_id instead of visit_id for declarations
        declarations_visit_id = str(visit_origin_id) if visit_origin_id else None
        if declarations_visit_id:
            cursor.execute(declarations_query, (declarations_visit_id,))
        else:
            cursor.execute("SELECT 1 WHERE 1=0")  # Return empty result if no origin_id
        declarations_data = convert_data(cursor)
        
        # Format declarations data
        declarations = []
        for decl in declarations_data:
            declarations.append({
                'id': decl['id'],
                'user_id': decl['user_id'],
                'type': decl['type'],
                'customs_number': decl['customs_number'],
                'representative_voen': decl['representative_voen'],
                'representative_name': decl['representative_name'],
                'company_voen': decl['company_voen'],
                'company_name': decl['company_name'],
                'created_at': decl['created_at'].isoformat() if decl.get('created_at') else None
            })
        
        extract_integer = lambda x: x[0] if isinstance(x, tuple) else x
        converted_date = datetime.fromtimestamp(visit_data['created_timestamp']/1000).strftime('%d-%m-%Y')
        del visit_data['created_timestamp']
        visit_data['created_timestamp'] = converted_date


        all = {
            "data": data,
            "visit_data": visit_data,
            "profile_data": profile_data,
            "declarations": declarations,
            "count": extract_integer(count[0])
        }
        cursor.close()

        return Response(all)
    

class ServiceListApi(APIView):
    def get(self,request):
        cursor = get_connection()
        customer_id = request.GET.get('customer_id',None)
        services_query = """SELECT DISTINCT ON (ds.origin_id) 
                            ds."name", 
                            ds.id,
                            ds.origin_id
                        FROM stat.dim_service AS ds
                        INNER JOIN stat.fact_visit_transaction fvt ON fvt.service_key = ds.id
                        INNER JOIN stat.dim_visit dv ON dv.id = fvt.visit_key
                            """
        if customer_id:
            services_query+= f"""inner join stat.dim_customer dc on dc.id::varchar = dv.custom_1
                                where dc.id = {customer_id}"""
        services_query+= """ORDER BY ds.origin_id, ds.id DESC;"""
        cursor.execute(services_query)
        service_data = convert_data(cursor)
        return Response(service_data)

class BranchListApi(APIView):
    def get(self,request):
        cursor = get_connection()
        branches_query = """SELECT db."name", db.id FROM stat.dim_branch AS db"""
        cursor.execute(branches_query)
        service_data = convert_data(cursor)
        return Response(service_data)


class RiskFinUpdateApi(APIView):
    """
    API endpoint for updating or inserting risk FIN records.
    Updates in both statdb and qp_agent databases.
    If FIN exists in table, updates it; otherwise inserts new record.
    
    Parameters:
        - fin: FIN code (required)
        - is_risk: Boolean flag indicating if FIN is at risk (default: False)
        - note: Optional text note/comment for the FIN record
    """
    
    def _get_qp_agent_connection(self):
        """Get connection to qp_agent database"""
        conn = psycopg2.connect(
            dbname=settings.QP_AGENT_DB_NAME,
            user=settings.QP_AGENT_DB_USER,
            password=settings.QP_AGENT_DB_PASSWORD,
            host=settings.QP_AGENT_DB_HOST,
            port=settings.QP_AGENT_DB_PORT
        )
        # search_path'i qp_agent schema'sına ayarla
        cursor = conn.cursor()
        cursor.execute("SET search_path TO qp_agent, public")
        # search_path'i kontrol et
        cursor.execute("SHOW search_path")
        search_path = cursor.fetchone()[0]
        logger.info(f"QP_AGENT DB: search_path = {search_path}")
        
        # Tabloyu kontrol et
        cursor.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'visits_risk_fin'
        """)
        tables = cursor.fetchall()
        logger.info(f"QP_AGENT DB: Found tables: {tables}")
        
        # qp_agent schema'sında tablo var mı kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'qp_agent' 
                AND table_name = 'visits_risk_fin'
            )
        """)
        table_exists = cursor.fetchone()[0]
        logger.info(f"QP_AGENT DB: qp_agent.visits_risk_fin exists: {table_exists}")
        
        cursor.close()
        return conn
    
    def _upsert_risk_fin(self, conn, fin, is_risk, note=None, schema=None):
        """Execute UPSERT query for risk_fin table"""
        cursor = conn.cursor()
        # Schema belirtilmişse kullan, yoksa public schema
        table_name = f"{schema}.visits_risk_fin" if schema else "visits_risk_fin"
        
        # Debug: search_path'i kontrol et
        cursor.execute("SHOW search_path")
        search_path = cursor.fetchone()[0]
        logger.info(f"_upsert_risk_fin: Using table_name = {table_name}, search_path = {search_path}")
        
        upsert_query = f"""
            INSERT INTO {table_name} (fin, is_risk, note, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (fin) 
            DO UPDATE SET 
                is_risk = EXCLUDED.is_risk,
                note = EXCLUDED.note,
                updated_at = NOW()
            RETURNING id, fin, is_risk, note, created_at, updated_at;
        """
        logger.info(f"_upsert_risk_fin: Executing query: {upsert_query[:100]}...")
        cursor.execute(upsert_query, (fin, is_risk, note))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def post(self, request):
        statdb_cursor = None
        statdb_conn = None
        qp_agent_conn = None
        try:
            data = json.loads(request.body)
            fin = data.get('fin')
            is_risk = data.get('is_risk', False)
            note = data.get('note', None)
            
            if not fin:
                return Response(
                    {"error": "FIN parameter is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate boolean value
            if not isinstance(is_risk, bool):
                is_risk = str(is_risk).lower() in ('true', '1', 'yes')
            
            # Get connection to statdb (main database)
            statdb_cursor = get_connection()
            statdb_conn = statdb_cursor.connection
            
            # Update in statdb
            try:
                statdb_result = self._upsert_risk_fin(statdb_conn, fin, is_risk, note)
                statdb_conn.commit()
            except Exception as e:
                statdb_conn.rollback()
                return Response(
                    {"error": f"Error in statdb database: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get connection to qp_agent database
            qp_agent_conn = self._get_qp_agent_connection()
            
            # Update in qp_agent database
            try:
                # Schema belirtmeden dene (public schema veya search_path'te olabilir)
                logger.info(f"Attempting to update qp_agent database with fin={fin}")
                qp_agent_result = self._upsert_risk_fin(qp_agent_conn, fin, is_risk, note)
                qp_agent_conn.commit()
                logger.info(f"Successfully updated qp_agent database")
            except Exception as e:
                qp_agent_conn.rollback()
                error_msg = str(e)
                logger.error(f"Error in qp_agent database: {error_msg}")
                logger.error(f"Error type: {type(e).__name__}")
                return Response(
                    {
                        "error": f"Error in qp_agent database: {error_msg}",
                        "debug_info": {
                            "db_name": settings.QP_AGENT_DB_NAME,
                            "db_host": settings.QP_AGENT_DB_HOST,
                            "db_user": settings.QP_AGENT_DB_USER,
                            "error_type": type(e).__name__
                        }
                    }, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if statdb_result:
                response_data = {
                    "id": statdb_result[0],
                    "fin": statdb_result[1],
                    "is_risk": statdb_result[2],
                    "note": statdb_result[3],
                    "created_at": statdb_result[4].isoformat() if statdb_result[4] else None,
                    "updated_at": statdb_result[5].isoformat() if statdb_result[5] else None,
                    "message": "FIN updated successfully in both databases",
                    "statdb_updated": True,
                    "qp_agent_updated": True
                }
                statdb_cursor.close()
                qp_agent_conn.close()
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                statdb_cursor.close()
                if qp_agent_conn:
                    qp_agent_conn.close()
                return Response(
                    {"error": "Failed to insert/update FIN"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except psycopg2.IntegrityError as e:
            if statdb_conn:
                statdb_conn.rollback()
            if qp_agent_conn:
                qp_agent_conn.rollback()
            if statdb_cursor:
                statdb_cursor.close()
            if qp_agent_conn:
                qp_agent_conn.close()
            return Response(
                {"error": f"Database error: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            if statdb_conn:
                statdb_conn.rollback()
            if qp_agent_conn:
                qp_agent_conn.rollback()
            if statdb_cursor:
                statdb_cursor.close()
            if qp_agent_conn:
                qp_agent_conn.close()
            return Response(
                {"error": f"Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AudioRecordingApi(APIView):
    """
    API endpoint for retrieving OPUS audio recordings from Samba server.
    Returns OPUS audio file directly (no encryption).
    
    Parameters:
        - date: Recording date in YYYY-MM-DD format (required)
        - transaction_id: Transaction ID (required)
    """
    
    def _get_samba_file(self, date, transaction_id):
        """Retrieve OPUS file from Samba server"""
        try:
            # Samba connection məlumatları
            server = settings.SAMBA_SERVER_IP
            share = settings.SAMBA_SHARE_NAME
            username = settings.SAMBA_USERNAME
            password = settings.SAMBA_PASSWORD
            
            # Fayl yolu: recordings/YYYY-MM-DD/transaction_id.opus (forward slash istifadə et)
            file_path = f"recordings/{date}/{transaction_id}.opus"
            
            logger.info(f"Samba connection: server={server}, share={share}, file_path={file_path}")
            
            # Samba serverə qoşul
            connection = Connection(uuid.uuid4(), server, 445)
            connection.connect()
            
            session = Session(connection, username, password)
            session.connect()
            
            # TreeConnect üçün sadəcə share adını istifadə et
            tree = TreeConnect(session, share)
            tree.connect()
            
            logger.info(f"Trying to open file: {file_path}")
            
            # Faylı aç
            file_open = Open(tree, file_path)
            file_open.create(
                ImpersonationLevel.Impersonation,
                FilePipePrinterAccessMask.FILE_READ_DATA | FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
                0,  # file_attributes
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN,
                CreateOptions.FILE_NON_DIRECTORY_FILE
            )
            
            # Faylı oxu
            file_data = file_open.read(0, file_open.end_of_file)
            
            # Bağla
            file_open.close()
            tree.disconnect()
            session.disconnect()
            connection.disconnect()
            
            logger.info(f"File read successfully, size: {len(file_data)} bytes")
            return file_data
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Samba error details: server={settings.SAMBA_SERVER_IP}, share={settings.SAMBA_SHARE_NAME}, file_path=recordings/{date}/{transaction_id}.opus, error={error_str}")
            
            # Fayl tapılmadığında aydın mesaj ver
            if "STATUS_OBJECT_PATH_NOT_FOUND" in error_str or "path does not exist" in error_str.lower() or "0xc000003a" in error_str:
                raise FileNotFoundError(f"Audio file not found: recordings/{date}/{transaction_id}.opus")
            
            raise Exception(f"Samba server error: {error_str}")
    
    
    def get(self, request):
        try:
            date = request.GET.get('date')
            transaction_id = request.GET.get('transaction_id')
            
            if not date or not transaction_id:
                return Response(
                    {"error": "date and transaction_id parameters are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse date format - frontend'den "13-11-2025 14:22:10" formatında gelebilir
            parsed_date = None
            date_formats = [
                '%d-%m-%Y %H:%M:%S',  # 13-11-2025 14:22:10
                '%d-%m-%Y',            # 13-11-2025
                '%Y-%m-%d',             # 2025-11-13
                '%Y-%m-%d %H:%M:%S',    # 2025-11-13 14:22:10
            ]
            
            for date_format in date_formats:
                try:
                    parsed_date = datetime.strptime(date, date_format)
                    break
                except ValueError:
                    continue
            
            if not parsed_date:
                return Response(
                    {"error": f"Invalid date format: {date}. Supported formats: DD-MM-YYYY HH:MM:SS, DD-MM-YYYY, YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Samba'da axtarış üçün YYYY-MM-DD formatına çevir
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            
            # Samba serverdən OPUS faylı götür
            try:
                opus_data = self._get_samba_file(formatted_date, transaction_id)
            except FileNotFoundError as e:
                # Fayl tapılmadığında aydın mesaj ver
                return Response(
                    {"error": f"Audio file not found: recordings/{formatted_date}/{transaction_id}.opus"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                # Digər Samba xətaları
                logger.error(f"Samba connection error: {str(e)}")
                return Response(
                    {"error": f"Samba server error: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if not opus_data:
                return Response(
                    {"error": f"Audio file not found: recordings/{formatted_date}/{transaction_id}.opus"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            logger.info(f"OPUS file retrieved successfully, size: {len(opus_data)} bytes")
            
            # OPUS faylını birbaşa response et - şifrələmə yoxdur, decode lazım deyil
            # Modern browsers OPUS formatını native dəstəkləyir
            response = HttpResponse(opus_data, content_type='audio/ogg')
            response['Content-Disposition'] = f'inline; filename="{transaction_id}.opus"'
            response['Content-Length'] = len(opus_data)
            response['Accept-Ranges'] = 'bytes'
            
            return response
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
