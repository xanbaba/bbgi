
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


class StatisticsApiSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='visit_key')  # ID / Ziyarət
    visit_date = serializers.CharField()  # Tarix
    ticket_id = serializers.CharField()  # Bilet
    service_name = serializers.CharField(allow_null=True, required=False)  # Xidmət
    visit_duration = serializers.SerializerMethodField()  # Ziyarət müddəti

    # Declaration fields
    declaration = serializers.CharField(source='customs_number', allow_null=True, required=False)  # Bəyanname
    representation = serializers.CharField(source='type', allow_null=True, required=False)  # Təmsilçilik
    representative_name = serializers.CharField(allow_null=True, required=False)  # Təmsilçilik adı
    representative_voen = serializers.CharField(allow_null=True, required=False)  # Təmsilçilik VOEN
    represented_party_name = serializers.CharField(source='company_name', allow_null=True,
                                                   required=False)  # Təmsil olunan
    represented_party_voen = serializers.CharField(source='company_voen', allow_null=True,
                                                   required=False)  # Təmsil olunan VOEN

    status = serializers.CharField(allow_null=True, required=False)  # Status
    result = serializers.CharField(allow_null=True, required=False)  # Nəticə

    def get_visit_duration(self, obj):
        """Calculates formatted duration from transaction and wait time"""
        transaction_time = obj.get('total_transaction_time') or 0
        wait_time = obj.get('total_wait_time') or 0
        total_seconds = transaction_time + wait_time
        return format_time(total_seconds)


class VisitSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=50)
    ticket_id = serializers.CharField(max_length=10)
    service_name = serializers.CharField(max_length=100, allow_null=True, required=False)
    transactions_count = serializers.IntegerField()
    visit_key = serializers.IntegerField()
    visit_origin_id = serializers.IntegerField(allow_null=True, required=False)
    created_date = serializers.SerializerMethodField()
    total_transaction_time = serializers.SerializerMethodField()
    total_wait_time = serializers.SerializerMethodField()
    total_visit_time = serializers.SerializerMethodField()
    declarations = serializers.SerializerMethodField()
    result = serializers.CharField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()

    # New declaration fields
    declaration = serializers.CharField(max_length=255, allow_null=True, required=False)
    representation = serializers.CharField(max_length=255, allow_null=True, required=False)
    representative_name = serializers.CharField(max_length=255, allow_null=True, required=False)
    representative_voen = serializers.CharField(max_length=50, allow_null=True, required=False)
    represented_party_name = serializers.CharField(max_length=255, allow_null=True, required=False)
    represented_party_voen = serializers.CharField(max_length=50, allow_null=True, required=False)

    def get_total_wait_time(self, obj):
        return format_time(obj.get('total_wait_time'))

    def get_total_transaction_time(self, obj):
        return format_time(obj.get('total_transaction_time'))

    def get_total_visit_time(self, obj):
        total_wait_time = obj.get('total_wait_time', 0)
        total_transaction_time = obj.get('total_transaction_time', 0)

        if not total_wait_time:
            total_wait_time = 0

        if not total_transaction_time:
            total_transaction_time = 0

        total_visit_time = format_time(total_wait_time + total_transaction_time)
        return total_visit_time

    def get_created_date(self, obj):
        created_timestamp = obj.get('created_timestamp')
        if not created_timestamp:
            return None
        try:
            converted_date = datetime.fromtimestamp(created_timestamp / 1000).strftime('%d-%m-%Y %H:%M')
            return converted_date
        except Exception as e:
            print('Created date format error:', e)
            return None

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
    id = serializers.IntegerField(source='customer_id')
    count = serializers.IntegerField(source='visits')
    created_at = serializers.DateTimeField(format=time_format)
    # ADDED: last_visited field
    last_visited = serializers.DateTimeField(source='last_visited_at', format=time_format, allow_null=True,
                                             required=False)
    is_risk = serializers.BooleanField(default=False)
    risk_note = serializers.CharField(source='note', allow_null=True, required=False)

    def get_birth_date(self, obj):
        converted_date = obj['birth_date']
        if not obj['birth_date']:
            return None
        try:
            converted_date = datetime.strptime(converted_date, birth_date_format).strftime('%d-%m-%Y')
            return converted_date
        except Exception as e:
            print('Format error: ', e)
            return obj['birth_date']


class CustomerAllExportSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    father_name = serializers.CharField(max_length=255)
    birth_date = serializers.SerializerMethodField()
    pin = serializers.CharField(max_length=10)
    visits_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    # ADDED: last_visited field for export
    last_visited_at = serializers.DateTimeField(allow_null=True, required=False)

    COLUMN_MAPPING = {
        'first_name': 'Ad',
        'last_name': 'Soyad',
        'father_name': 'Ata adı',
        'birth_date': 'Doğum tarixi',
        'fin': 'FİN',
        'pin': 'FİN',  # alias
        'visits_count': 'Visit sayı',
        'visits': 'Visit sayı',  # alias
        'last_visited_at': 'Son ziyarət',
        'created_at': 'Yaradılma tarixi'
    }

    def __init__(self, *args, selected_columns: list | None =None, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_columns = [col for col in selected_columns if col]

    def get_birth_date(self, obj):
        converted_date = obj['birth_date']
        if not obj['birth_date']:
            return None
        try:
            converted_date = datetime.strptime(converted_date, birth_date_format).strftime('%d-%m-%Y')
            return converted_date
        except Exception as e:
            print('Format error: ', e)
            return obj['birth_date']

    def to_representation(self, instance):
        original_data = super().to_representation(instance)
        azerbaijani_data = {
            self.COLUMN_MAPPING[col]: original_data[col]
            for col in self.COLUMN_MAPPING
            if (col in original_data) and ((self.selected_columns and col in self.selected_columns) or (not self.selected_columns))
        }
        return azerbaijani_data


class VisitExportSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=50)
    ticket_id = serializers.CharField(max_length=10)
    service_name = serializers.CharField(max_length=100, allow_null=True, required=False)
    transactions_count = serializers.IntegerField()
    created_date = serializers.SerializerMethodField()
    total_transaction_time = serializers.SerializerMethodField()
    total_wait_time = serializers.SerializerMethodField()
    total_visit_time = serializers.SerializerMethodField()
    result = serializers.CharField(allow_null=True, required=False)
    status = serializers.CharField(allow_null=True, required=False)

    # New declaration fields
    declaration = serializers.CharField(max_length=255, allow_null=True, required=False)
    representation = serializers.CharField(max_length=255, allow_null=True, required=False)
    representative_name = serializers.CharField(max_length=255, allow_null=True, required=False)
    representative_voen = serializers.CharField(max_length=50, allow_null=True, required=False)
    represented_party_name = serializers.CharField(max_length=255, allow_null=True, required=False)
    represented_party_voen = serializers.CharField(max_length=50, allow_null=True, required=False)

    def get_total_wait_time(self, obj):
        return format_time(obj.get('total_wait_time'))

    def get_total_transaction_time(self, obj):
        return format_time(obj.get('total_transaction_time'))

    def get_total_visit_time(self, obj):
        total_wait_time = obj.get('total_wait_time', 0)
        total_transaction_time = obj.get('total_transaction_time', 0)

        if not total_wait_time:
            total_wait_time = 0

        if not total_transaction_time:
            total_transaction_time = 0

        total_visit_time = format_time(total_wait_time + total_transaction_time)
        return total_visit_time

    def get_created_date(self, obj):
        created_timestamp = obj.get('created_timestamp')
        if not created_timestamp:
            return None
        try:
            converted_date = datetime.fromtimestamp(created_timestamp / 1000).strftime('%d-%m-%Y')
            return converted_date
        except Exception as e:
            print('Created date format error:', e)
            return None

    def to_representation(self, instance):
        original_data = super().to_representation(instance)
        azerbaijani_data = {
            "Ad": original_data.get("first_name", "-"),
            "Soyad": original_data.get("last_name", "-"),
            "FIN": original_data.get("pin", "-"),
            "Bilet": original_data.get("ticket_id", "-"),
            "Xidmət": original_data.get("service_name", "-"),
            "Transaction sayı": original_data.get("transactions_count", 0),
            "Yaranma tarixi": original_data.get("created_date", "-"),
            "Gözləmə vaxtı": original_data.get("total_wait_time", "-"),
            "Transaction vaxtı": original_data.get("total_transaction_time", "-"),
            "Ziyarət müddəti": original_data.get("total_visit_time", "-"),
            "Bəyannamə": original_data.get("declaration", "-"),
            "Təmsilçilik": original_data.get("representation", "-"),
            "Təmsilçi adı": original_data.get("representative_name", "-"),
            "Təmsilçi VÖEN": original_data.get("representative_voen", "-"),
            "Təmsil olunan": original_data.get("represented_party_name", "-"),
            "Təmsil olunan VÖEN": original_data.get("represented_party_voen", "-"),
            "Status": original_data.get("status", "-"),
            "Nəticə": original_data.get("result", "-"),
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