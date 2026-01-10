
from rest_framework import serializers
from datetime import datetime, timedelta
from core.api.helper import format_time

time_format = "%d-%m-%Y %H:%M:%S"
date_key_format = '%Y%d%M'
birth_date_format = '%Y-%M-%d'
class CustomerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=20)
    father_name = serializers.CharField(max_length=100)
    birth_date = serializers.DateField()
    phone = serializers.CharField(max_length=20, allow_null=True, required=False)
    image = serializers.CharField(max_length=500, allow_null=True, required=False)
    is_risk = serializers.BooleanField(default=False)


class TransactionDataSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    create_timestamp = serializers.DateTimeField(format=time_format)
    waiting_time = serializers.SerializerMethodField()
    call_timestamp = serializers.DateTimeField(format=time_format)
    transaction_time = serializers.SerializerMethodField()
    outcome_key = serializers.CharField(allow_null=True, required=False)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    finish_time = serializers.SerializerMethodField()
    note = serializers.CharField(allow_null=True, required=False)
    result = serializers.IntegerField(allow_null=True, required=False)
    table = serializers.CharField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()

    def get_waiting_time(self,obj):
        return format_time(obj['waiting_time'])

    def get_transaction_time(self,obj):
        return format_time(obj['transaction_time'])
    
    def get_finish_time(self,obj):
        call_time = obj['call_timestamp']
        transaction_time = obj['transaction_time']
        print('sdsd',call_time)
        if call_time and transaction_time:
            finish_time = call_time + timedelta(seconds=transaction_time)
            finish_time = datetime.strftime(finish_time, time_format)
            return finish_time
        return None
    
    def get_status(self, obj):
        """Return status from database (dim_visit_event_type.name), default is 'Xidmət göstərildi'"""
        return obj.get('status', 'Xidmət göstərildi')


class StatisticSerializer(serializers.Serializer):
    date_key = serializers.SerializerMethodField()
    branch_name = serializers.CharField(max_length=255)
    branch_id = serializers.IntegerField()
    service_name = serializers.CharField(max_length=255)
    service_id = serializers.IntegerField()
    ticket_id = serializers.CharField(max_length=50)
    waiting_time = serializers.SerializerMethodField()
    call_timestamp = serializers.DateTimeField(format=time_format)
    transaction_time = serializers.SerializerMethodField()
    created_date = serializers.DateTimeField(source = 'create_timestamp',format=time_format)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    pin = serializers.CharField(max_length=50)
    father_name = serializers.CharField(max_length=255)
    birth_date = serializers.CharField(max_length=20)
    result = serializers.CharField(max_length=255, allow_null=True, required=False)
    outcome_key = serializers.CharField(max_length=255, allow_null=True, required=False)
    staff_first_name = serializers.CharField(max_length=255)
    staff_last_name = serializers.CharField(max_length=255)
    staff_name = serializers.CharField(max_length=255)
    finish_time = serializers.SerializerMethodField()
    total_visit_time = serializers.SerializerMethodField()

    def get_waiting_time(self,obj):
        return format_time(obj['waiting_time'])

    def get_transaction_time(self,obj):
        return format_time(obj['transaction_time'])
    
    def get_total_visit_time(self,obj):
        transaction_time = obj['transaction_time']
        waiting_time = obj['waiting_time']

        if transaction_time and waiting_time:
            total_time = format_time(transaction_time + waiting_time)
            return total_time
        
        return None

    
    def get_date_key(self,obj):
        if not obj['date_key']:
            return obj['date_key']
        
        converted_date= datetime.strptime(str(obj['date_key']), date_key_format).strftime(format = time_format)
        return converted_date
    
    def get_finish_time(self,obj):
        call_time = obj['call_timestamp']
        transaction_time = obj['transaction_time']
        if call_time and transaction_time:
            finish_time = call_time + timedelta(seconds=transaction_time)
            finish_time = datetime.strftime(finish_time, time_format)
            return finish_time
        
        return None


class VisitSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=50)
    ticket_id = serializers.CharField(max_length=10)
    service_name = serializers.CharField(max_length=100)
    transactions_count = serializers.IntegerField()
    visit_key = serializers.IntegerField()
    created_date = serializers.SerializerMethodField(source = 'created_timestamp')
    total_transaction_time = serializers.SerializerMethodField()
    total_wait_time = serializers.SerializerMethodField()
    total_visit_time =  serializers.SerializerMethodField()
    declarations = serializers.SerializerMethodField()
    result = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()

    def get_total_wait_time(self,obj):
        return format_time(obj['total_wait_time'])

    def get_total_transaction_time(self,obj):
        return format_time(obj['total_transaction_time'])   
    
    def get_total_visit_time(self,obj):

        total_wait_time = obj.get('total_wait_time',0)
        total_transaction_time = obj.get('total_transaction_time',0)
        if not total_wait_time:
            total_wait_time = 0
        
        if not total_transaction_time:
            total_transaction_time = 0
            
        total_visit_time = format_time(total_wait_time+ total_transaction_time)
        return total_visit_time

    def get_created_date(self,obj):
        converted_date = datetime.fromtimestamp(obj['created_timestamp']/1000).strftime('%d-%m-%Y')
        return converted_date
    
    def get_birth_date(self,obj):
        if not obj.get('birth_date'):
            return None
        try:
            if isinstance(obj['birth_date'], str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%Y-%M-%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        converted_date = datetime.strptime(obj['birth_date'], fmt).strftime('%d-%m-%Y')
                        return converted_date
                    except ValueError:
                        continue
                # If no format matches, return as is
                return obj['birth_date']
            else:
                # If it's a date object
                converted_date = obj['birth_date'].strftime('%d-%m-%Y')
                return converted_date
        except Exception as e:
            print('Birth date format error: ',e)
            return obj.get('birth_date')
    
    def get_declarations(self, obj):
        """Return declarations data as list"""
        declarations = obj.get('declarations', [])
        if not declarations:
            return []
        
        return declarations
    
    def get_status(self, obj):
        """Return status from database (last transaction's dim_visit_event_type.name), default is 'Xidmət göstərildi'"""
        return obj.get('status', 'Xidmət göstərildi')


class CustomerAllSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    father_name = serializers.CharField(max_length=255)
    birth_date = serializers.SerializerMethodField()  
    pin = serializers.CharField(max_length=10)
    phone = serializers.CharField(max_length=20, allow_null=True, required=False)
    id = serializers.IntegerField(source = 'customer_id')
    count = serializers.IntegerField(source = 'visits')
    created_at = serializers.DateTimeField(format=time_format)
    is_risk = serializers.BooleanField(default=False)
    risk_note = serializers.CharField(source='note', allow_null=True, required=False)
    
    def get_birth_date(self,obj):
        converted_date = obj['birth_date']
        if not obj['birth_date']:
            return None
        try:
            converted_date = datetime.strptime(converted_date,birth_date_format).strftime('%d-%m-%Y')
            return converted_date
        except Exception as e:
            print('Format error: ',e)
            return obj['birth_date']
    
class CustomerAllExportSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    father_name = serializers.CharField(max_length=255)
    birth_date = serializers.SerializerMethodField()  
    fin = serializers.CharField(max_length=10,source = 'pin')
    visit_count = serializers.IntegerField(source = 'visits')
    created_at = serializers.DateTimeField()

    def get_birth_date(self,obj):
        converted_date = obj['birth_date']
        if not obj['birth_date']:
            return None
        try:
            converted_date = datetime.strptime(converted_date,birth_date_format).strftime('%d-%m-%Y')
            return converted_date
        except Exception as e:
            print('Format error: ',e)
            return obj['birth_date']
        
    def to_representation(self, instance):
        original_data = super().to_representation(instance)
        azerbaijani_data = {
            "Ad": original_data["first_name"],
            "Soyad": original_data["last_name"],
            "Ata adı": original_data["father_name"],
            "Doğum tarixi": original_data["birth_date"],
            "FİN": original_data["fin"],
            "Visit sayı": original_data["visit_count"],
        }
        return azerbaijani_data


class VisitExportSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=50)
    ticket_id = serializers.CharField(max_length=10)
    service_name = serializers.CharField(max_length=100)
    transactions_count = serializers.IntegerField()
    created_date = serializers.SerializerMethodField(source = 'created_timestamp')
    total_transaction_time = serializers.SerializerMethodField()
    total_wait_time = serializers.SerializerMethodField()
    total_visit_time =  serializers.SerializerMethodField()

    def get_total_wait_time(self,obj):
        return format_time(obj['total_wait_time'])

    def get_total_transaction_time(self,obj):
        return format_time(obj['total_transaction_time'])   
    
    def get_total_visit_time(self,obj):

        total_wait_time = obj.get('total_wait_time',0)
        total_transaction_time = obj.get('total_transaction_time',0)
        if not total_wait_time:
            total_wait_time = 0
        
        if not total_transaction_time:
            total_transaction_time = 0
            
        total_visit_time = format_time(total_wait_time+ total_transaction_time)
        return total_visit_time

    def get_created_date(self,obj):
        converted_date = datetime.fromtimestamp(obj['created_timestamp']/1000).strftime('%d-%m-%Y')
        return converted_date
    

    def to_representation(self, instance):
        original_data = super().to_representation(instance)
        azerbaijani_data = {
            "Ad": original_data["first_name"],
            "Soyad": original_data["last_name"],
            "FIN": original_data["pin"],
            "Bilet_id": original_data["ticket_id"],
            "Servis": original_data["service_name"],
            "Transaction sayı": original_data["transactions_count"],
            "Yaranma tarixi": original_data["created_date"],
            "Ümumi transaction vaxtı": original_data["total_transaction_time"],
            "Ümumi ziyarət vaxtı": original_data["total_visit_time"],
        }
        return azerbaijani_data
    
class StatisticExportSerializer(serializers.Serializer):
    service_name = serializers.CharField(max_length=255)
    ticket_id = serializers.CharField(max_length=50)
    waiting_time = serializers.SerializerMethodField()
    call_timestamp = serializers.DateTimeField(format=time_format)
    transaction_time = serializers.SerializerMethodField()
    created_date = serializers.DateTimeField(source = 'create_timestamp',format=time_format)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    pin = serializers.CharField(max_length=50)
    father_name = serializers.CharField(max_length=255)
    birth_date = serializers.CharField(max_length=20)
    outcome_key = serializers.CharField(max_length=255, allow_null=True, required=False)
    staff_name = serializers.CharField(max_length=255)
    finish_time = serializers.SerializerMethodField()

    def get_waiting_time(self,obj):
        return format_time(obj['waiting_time'])

    def get_transaction_time(self,obj):
        return format_time(obj['transaction_time'])
    
    def get_total_visit_time(self,obj):
        transaction_time = obj['transaction_time']
        waiting_time = obj['waiting_time']

        if transaction_time and waiting_time:
            total_time = format_time(transaction_time + waiting_time)
            return total_time
        
        return None

    
    def get_date_key(self,obj):
        if not obj['date_key']:
            return obj['date_key']
        
        converted_date= datetime.strptime(str(obj['date_key']), date_key_format).strftime(format = time_format)
        return converted_date
    
    def get_finish_time(self,obj):
        call_time = obj['call_timestamp']
        transaction_time = obj['transaction_time']
        if call_time and transaction_time:
            finish_time = call_time + timedelta(seconds=transaction_time)
            finish_time = datetime.strftime(finish_time, time_format)
            return finish_time
        
        return None
    
    def to_representation(self, instance):
        original_data = super().to_representation(instance)
        # Azərbaycan dilində `key`-lərin map olunması
        azerbaijani_data = {
            "Servis": original_data["service_name"],
            "Bilet": original_data["ticket_id"],
            "Gözləmə vaxtı": original_data["waiting_time"],
            "Çağrılma zamanı": original_data["call_timestamp"],
            "Transaction vaxtı": original_data["transaction_time"],
            "Yaranma tarixi": original_data["created_date"],
            "Ad": original_data["first_name"],
            "Soyad": original_data["last_name"],
            "FIN": original_data["pin"],
            "Ata adı": original_data["father_name"],
            "Doğum_tarixi": original_data["birth_date"],
            "Outcome key": original_data["outcome_key"],
            "İşçi username": original_data["staff_name"],
            "Bitmə_zamanı": original_data["finish_time"],
        }
        return azerbaijani_data