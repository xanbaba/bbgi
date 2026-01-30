# Gömrük Xidmətləri İdarəetmə Sistemi - Texniki Dokümantasiya

## 1. Sistem Arxitekturası

### 1.1. Ümumi Arxitektura

Sistem 3 əsas komponentdən ibarətdir:

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Local Agent    │────────▶│  Customs Project │────────▶│Customs Statistics│
│  (Windows)      │         │   (Django API)   │         │   (Django API)   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
       │                              │                              │
       │                              │                              │
       ▼                              ▼                              ▼
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Samba Server   │         │  PostgreSQL DB   │         │  PostgreSQL DB  │
│  (OPUS files)   │         │  (qp_agent)      │         │  (stat)         │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

### 1.2. Texnologiyalar

**Local Agent:**

- Python
- Flask (REST API)
- PyAudio (səs yazma)
- PyInstaller (exe build)
- SQLAlchemy (database)
- pysmb (Samba upload)
- ffmpeg (audio conversion)

**Customs Project:**

- Python
- Django
- Django REST Framework
- PostgreSQL (database)
- drf-spectacular (API documentation)
- django-cors-headers (CORS)

**Customs Statistics:**

- Python
- Django
- Django REST Framework
- PostgreSQL (database)
- pandas (data processing)
- openpyxl (Excel export)
- mrz (passport reading)
- smbprotocol (Samba file access)

---

## 2. Database Struktur

### 2.1. Database-lər

Sistem 3 əsas database istifadə edir:

1. **qp_agent** - Ana database (visit, declaration, note, permission)
2. **stat** - Statistika database (fact və dim cədvəlləri)
3. **Local SQLite** - Local Agent üçün (recording log, upload queue)

### 2.2. Əsas Cədvəllər

#### 2.2.1. qp_agent Database

**visits_visit:**

```sql
- visit_id (VARCHAR, PRIMARY KEY)
- first_name, last_name, father_name
- customer_type, fin, passport_number
- birth_date, phone, image
- branch_id, service_id
- created_at, updated_at
```

**visits_declaration:**

```sql
- id (SERIAL, PRIMARY KEY)
- visit_id (VARCHAR, FOREIGN KEY)
- user_id, type
- customs_number
- representative_voen, representative_name
- company_voen, company_name
- created_at
```

**visits_note:**

```sql
- id (SERIAL, PRIMARY KEY)
- visit_id (VARCHAR, FOREIGN KEY)
- user_id, content
- status (INTEGER: 1=təmin edildi, 0=təmin edilmədi)
- action, table
- created_at
```

**record_permissions:**

```sql
- id (SERIAL, PRIMARY KEY)
- branch_id (VARCHAR, UNIQUE, nullable)
- user_id (VARCHAR, UNIQUE, nullable)
- is_enabled (BOOLEAN)
- created_at, updated_at
```

**schedule_groups:**

```sql
- id (SERIAL, PRIMARY KEY)
- name (VARCHAR)
- lifetime (INTEGER)
- unit (VARCHAR: Year/Month/Day)
- is_active (BOOLEAN)
- created_at, updated_at
```

**schedule_group_services:**

```sql
- group_id (INTEGER, FOREIGN KEY)
- service_id (INTEGER, FOREIGN KEY)
- added_at (TIMESTAMP)
```

**visits_service_auto_end_permission:**

```sql
- id (SERIAL, PRIMARY KEY)
- service_id (INTEGER)
- branch_id (INTEGER)
- is_enabled (BOOLEAN)
- created_at, updated_at
- UNIQUE(service_id, branch_id)
```

**visits_service_accept_permission:**

```sql
- id (SERIAL, PRIMARY KEY)
- service_id (INTEGER)
- branch_id (INTEGER)
- is_accept (BOOLEAN)
- created_at, updated_at
- UNIQUE(service_id, branch_id)
```

**visits_risk_fin:**

```sql
- id (SERIAL, PRIMARY KEY)
- fin (VARCHAR, UNIQUE)
- is_risk (BOOLEAN)
- note (TEXT)
- created_at, updated_at
```

#### 2.2.2. stat Database

**stat.fact_visit_transaction:**

```sql
- id (BIGINT, PRIMARY KEY)
- visit_key, branch_key, service_key, staff_key
- date_key, time_key, time_seconds
- create_timestamp, call_timestamp
- waiting_time, transaction_time
- outcome_key, visit_outcome_key
```

**stat.dim_visit:**

```sql
- id (BIGINT, PRIMARY KEY)
- origin_id (VARCHAR) - visits_visit.visit_id ilə eşləşir
- ticket_id, custom_1, custom_2
- created_timestamp
```

**stat.dim_customer:**

```sql
- id (BIGINT, PRIMARY KEY)
- first_name, last_name, father_name
- pin (FIN), birth_date, phone
- visits_count, created_at
```

**stat.dim_branch:**

```sql
- id (BIGINT, PRIMARY KEY)
- name, origin_id
```

**stat.dim_service:**

```sql
- id (BIGINT, PRIMARY KEY)
- name, origin_id
```

**stat.dim_staff:**

```sql
- id (BIGINT, PRIMARY KEY)
- name, first_name, last_name
- origin_id
```

**stat.active_recordings:**

```sql
- id (SERIAL, PRIMARY KEY)
- user_id, branch_id, visit_id
- transaction_id (VARCHAR, UNIQUE)
- started_at, mic_connected
```

#### 2.2.3. Local SQLite (Local Agent)

**voice_recording_logs:**

```sql
- id (INTEGER, PRIMARY KEY)
- visit_id, transaction_id
- event_type, user_id, branch_id
- created_at
```

**active_recordings:**

```sql
- id (INTEGER, PRIMARY KEY)
- user_id, branch_id, visit_id
- transaction_id (UNIQUE)
- started_at, mic_connected
```

**upload_queue:**

```sql
- id (INTEGER, PRIMARY KEY)
- file_path (TEXT)
- status (TEXT: pending/failed/completed)
- retries (INTEGER)
- last_retry (TIMESTAMP)
- created_at
```

### 2.3. Database Sinxronizasiya

**Sinxron əməliyyatlar:**

- Ana database (qp_agent) əməliyyatları sinxron olaraq icra olunur

**Asinxron əməliyyatlar:**

- Stat database-ə yazma asinxron olaraq baş verir (threading.Thread)
- Bu performansı artırır və ana əməliyyatları yavaşlatmır

**Nümunə:**

```python
def insert_visit(visit_data):
    # Ana database-ə insert (sinxron)
    qp_db.execute(query, params)
  
    # Stat database-ə insert (asinxron)
    _execute_stat_async(stat_query, params)
```

---

## 3. Local Agent (Windows Agent)

### 3.1. Arxitektura

```
local_agent/
├── app.py                 # Flask API server
├── record/
│   ├── recorder.py        # Səs yazma məntiqi
│   ├── processes.py        # WAV → OPUS conversion
│   ├── devices.py         # Mikrofon cihaz idarəetməsi
│   └── upload_sambo.py    # Samba upload (köhnə)
├── uploader/
│   ├── upload_manager.py  # Upload queue manager
│   └── upload_queue.py    # SQLite queue
├── db/
│   ├── database.py        # DatabaseManager
│   └── models.py          # SQLAlchemy models
├── config/
│   ├── config.json        # Mikrofon konfiqurasiyası
│   ├── samba_config.json  # Samba credentials
│   └── db_config.py       # Database konfiqurasiyası
└── tools/
    └── ffmpeg.exe         # Audio converter
```

### 3.2. Əsas Komponentlər

#### 3.2.1. Recorder (record/recorder.py)

**Funksiyalar:**

- Mikrofon vasitəsilə səs yazma
- WAV formatında fayl yaratma
- Mikrofon ayrılma/reconnect idarəetməsi
- Disk space yoxlaması
- ActiveRecording database entry yaratma

**Əsas metodlar:**

```python
class Recorder:
    def start(transaction_id, user_id, branch_id, visit_id)
    def stop() -> str  # WAV file path qaytarır
    def set_device(device_index)
```

**Mikrofon idarəetməsi:**

- İlkin mikrofon adı saxlanılır
- Mikrofon ayrıldıqda eyni mikrofonu tapmağa çalışır
- Fərqli mikrofon qəbul edilmir
- Mikrofon statusu database-də qeydə alınır

#### 3.2.2. Process Stop (record/processes.py)

**Funksiyalar:**

- WAV → OPUS conversion (ffmpeg)
- Database log yaratma
- Upload queue-yə əlavə etmə
- Temp WAV faylını silmə

**Conversion parametrləri:**

- Format: OPUS
- Bitrate: 24k
- Application: voip
- Compression: 10

#### 3.2.3. Upload Manager (uploader/upload_manager.py)

**Funksiyalar:**

- Upload queue idarəetməsi
- Samba server bağlantısı
- Retry mexanizmi (max 3 dəfə)
- Network stats tracking
- Timeout hesablama (fayl ölçüsünə görə)

**Upload prosesi:**

1. Queue-dan pending faylları götürür
2. Samba server bağlantısını yoxlayır
3. Faylı yükləyir (recordings/YYYY-MM-DD/transaction_id.opus)
4. Uğurlu olduqda lokal faylı silir
5. Uğursuz olduqda retry edir

#### 3.2.4. Database Manager (db/database.py)

**Funksiyalar:**

- VoiceRecordingLog yaratma
- ActiveRecording idarəetməsi (start/stop/update)
- Recording icazə yoxlaması
- Mikrofon status yeniləməsi
- Köhnə recording-ləri təmizləmə

**İcazə yoxlaması:**

```python
def is_branch_recording_enabled(branch_id, user_id) -> bool:
    # Həm branch, həm də user üçün permission olmalıdır
    branch_permission = RecordPermission.query.filter_by(
        branch_id=branch_id, is_enabled=True
    ).first()
  
    user_permission = RecordPermission.query.filter_by(
        user_id=user_id, is_enabled=True
    ).first()
  
    return branch_permission is not None and user_permission is not None
```

### 3.3. API Endpoint-lər

**Flask API (app.py):**

```
GET  /api/devices              # Mikrofon cihazlar siyahısı
POST /api/set_device           # Mikrofon seçimi
POST /api/record_event         # Recording başlat/bitir
GET  /api/upload_status        # Upload status
POST /api/set_samba            # Samba credentials
GET  /api/get_samba            # Samba credentials
POST /api/admin/cleanup_active_recordings  # Manual cleanup
```

**record_event endpoint:**

```python
POST /api/record_event
{
    "event_type": "visit_call" | "visit_next" | "visit_end" | "visit_finish",
    "visit_id": "string",
    "transaction_id": "string",
    "user_id": "string",
    "branch_id": "string"
}
```

### 3.4. Konfiqurasiya

**config/config.json:**

```json
{
    "MICROPHONE_INDEX": 1
}
```

**config/samba_config.json:**

```json
{
    "SERVER_IP": "23.88.99.92",
    "SERVER_NAME": "DEBIAN-SERVER",
    "SHARE_NAME": "Share",
    "USERNAME": "sambauser",
    "PASSWORD": "password"
}
```

**.env faylı:**

```env
DATABASE_URL=postgresql://user:pass@host:port/dbname
DB_USER=stat
DB_PASSWORD=stat
DB_HOST=94.130.176.68
DB_PORT=5432
DB_NAME=statdb
QP_DB_USER=qpagent
QP_DB_PASSWORD=qpagent
QP_DB_HOST=94.130.176.68
QP_DB_PORT=5432
QP_DB_NAME=qpagentdb
FLASK_ENV=production
```

### 3.5. Build Prosesi

**PyInstaller build:**

```bash
pyinstaller build.spec --clean --noconfirm
```

**build.spec konfiqurasiyası:**

- Hidden imports
- Data files (config, tools)
- Exclude modules
- Console/Windowed mode

**Build-dən sonra:**

- `dist/local_agent/` klasöründə exe yaranır
- `.env`, `config/`, `tools/ffmpeg.exe` kopyalanmalıdır
- `recordings/` klasörü avtomatik yaranır

---

## 4. Customs Project (Visit İdarəetmə API)

### 4.1. Arxitektura

```
customs_project/
├── customs_project/
│   ├── settings.py         # Django settings
│   └── urls.py             # Root URL config
└── visits/
    ├── views.py            # API views
    ├── serializers.py      # DRF serializers
    ├── models.py           # Django models (boş)
    ├── db.py               # Database connection classes
    ├── db_operations.py   # Database operations
    ├── external_api.py     # External API client
    ├── excel_export.py    # Excel export
    └── urls.py             # URL routing
```

### 4.2. Database Connection

**3 database connection class:**

```python
class Database:      # Ana database (default)
class QpDatabase:    # qp_agent database
class StatDatabase:  # stat database
```

**Konfiqurasiya (decouple):**

```python
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
QP_DB_NAME, QP_DB_USER, QP_DB_PASSWORD, QP_DB_HOST, QP_DB_PORT
STAT_DB_NAME, STAT_DB_USER, STAT_DB_PASSWORD, STAT_DB_HOST, STAT_DB_PORT
```

### 4.3. API Endpoint-lər

#### 4.3.1. Visit Endpoint-ləri

**GET /api/visits/**

- Visitləri pagination ilə gətirir
- Query parametrləri:
  - `page`, `page_size`
  - `visit_ids` (vergüllə ayrılmış)
  - `customs_number`, `fin`
  - `is_accept=true`
- Response: `{count, next, previous, results}`

**POST /api/visits/**

- Yeni visit yaradır
- Request body: VisitSerializer
- Image base64 formatında göndərilir
- Auto-end permission yoxlanılır

**GET /api/visits/{visit_id}/**

- Visit detalını gətirir
- Eyni customs_number olan visitləri də göstərir

**PUT/PATCH /api/visits/{visit_id}/**

- Visit məlumatlarını yeniləyir
- Partial update dəstəklənir

#### 4.3.2. Declaration Endpoint-ləri

**POST /api/declarations/**

- Yeni declaration əlavə edir

**PUT/PATCH /api/declarations/{id}/**

- Declaration yeniləyir

**DELETE /api/declarations/{id}/**

- Declaration silir

#### 4.3.3. Note Endpoint-ləri

**POST /api/visits/{visit_id}/notes/**

- Visit-ə note əlavə edir

#### 4.3.4. Permission Endpoint-ləri

**Branch Permissions:**

- `GET /api/branches/` - Branch-lar və permission statusu
- `POST /api/branches/permissions/` - Permission yenilə
- `DELETE /api/branches/{id}/permissions/` - Permission sil
- `GET /api/branches/active/` - Aktiv branch-lar
- `GET /api/branches/inactive/` - Qeyri-aktiv branch-lar

**User Permissions:**

- `GET /api/users/` - User-lar və permission statusu
- `POST /api/users/permissions/` - Permission yenilə
- `DELETE /api/users/{id}/permissions/` - Permission sil
- `GET /api/users/active/` - Aktiv user-lar
- `GET /api/users/inactive/` - Qeyri-aktiv user-lar

#### 4.3.5. Schedule Group Endpoint-ləri

- `GET /api/schedule-groups/` - Bütün group-lar
- `POST /api/schedule-groups/` - Yeni group yarat
- `GET /api/schedule-groups/{id}/` - Group detalı
- `PUT/PATCH /api/schedule-groups/{id}/` - Group yenilə
- `DELETE /api/schedule-groups/{id}/` - Group sil
- `GET /api/services/` - Bütün servislər
- `POST /api/schedule-groups/services/` - Group-a servis əlavə et
- `PUT /api/schedule-groups/services/` - Group servislərini yenilə
- `DELETE /api/schedule-groups/{group_id}/services/{service_id}/` - Servis sil

#### 4.3.6. Service Permission Endpoint-ləri

**Auto-End Permissions:**

- `GET /api/services/auto-end-permissions/` - Bütün permission-lar
- `POST /api/services/auto-end-permissions/?branch_id=X` - Permission yenilə
- `GET /api/services/auto-end-permissions/active/` - Aktiv permission-lar
- `GET /api/services/auto-end-permissions/inactive/` - Qeyri-aktiv permission-lar

**Accept Permissions:**

- `GET /api/services/accept-permissions/` - Bütün permission-lar
- `POST /api/services/accept-permissions/?branch_id=X` - Permission yenilə
- `GET /api/services/accept-permissions/active/` - Aktiv permission-lar
- `GET /api/services/accept-permissions/inactive/` - Qeyri-aktiv permission-lar

#### 4.3.7. Active Recordings

- `GET /api/active-recordings/` - Aktiv recording-lar siyahısı

#### 4.3.8. Excel Export

- `GET /api/visits/export-excel/?date=YYYY-MM-DD&operator_id=X` - Excel export

### 4.4. Database Operations (db_operations.py)

**Sinxron/Asinxron pattern:**

```python
def insert_visit(visit_data):
    # Ana database (sinxron)
    qp_db.execute(query, params)
  
    # Stat database (asinxron)
    _execute_stat_async(stat_query, params)
```

**Əməliyyatlar:**

- `insert_visit`, `update_visit`
- `insert_declaration`, `update_declaration`, `delete_declaration`
- `insert_note`
- `upsert_branch_permission`, `delete_branch_permission`
- `upsert_user_permission`, `delete_user_permission`
- `insert_schedule_group`, `update_schedule_group`, `delete_schedule_group`
- `insert_schedule_group_service`, `delete_schedule_group_service`

### 4.5. External API Client (external_api.py)

**ExternalAPIClient:**

- Qmatic API ilə inteqrasiya
- Visit avtomatik bitirmə

**Metodlar:**

```python
add_visit_to_service_point(branch_id, visit_id)
end_visit(branch_id, visit_id)
process_visit_auto_end(branch_id, visit_id)  # İki addımı birlikdə
```

### 4.6. Deployment

**Gunicorn:**

```bash
gunicorn customs_project.wsgi:application --bind 0.0.0.0:8000
```

**Docker (docker-compose.yml):**

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=...
```

---

## 5. Customs Statistics (Statistika və Hesabatlar API)

### 5.1. Arxitektura

```
customs-statistcs/
├── bbgi/
│   ├── settings.py         # Django settings
│   └── connection.py       # Database connection
└── core/
    ├── api/
    │   ├── views.py        # API views
    │   ├── serializers.py  # DRF serializers
    │   └── urls.py          # URL routing
    ├── mrz_input.py         # MRZ passport reading
    └── models.py            # Django models (boş)
```

### 5.2. API Endpoint-lər

#### 5.2.1. Passport API

**POST /api/passport/**

- Pasport MRZ kodunu oxuyur
- Hospital Service (SOAP) vasitəsilə müştəri məlumatlarını gətirir
- Response: `{name, surname, father_name, image, fin, birth_date}`

**MRZ formatları:**

- TD1: 90 simvol
- TD2: 72 simvol
- TD3: 88 simvol

#### 5.2.2. Statistika API

**GET /api/report/**

- Əsas statistika hesabatı
- Query parametrləri:
  - `minDateSelected`, `maxDateSelected`
  - `callMinDateSelected`, `callMaxDateSelected`
  - `finishMinDateSelected`, `finishMaxDateSelected`
  - `waitMinDateSelected`, `waitMaxDateSelected`
  - `transacMinDateSelected`, `transacMaxDateSelected`
  - `selectedBranches[]`, `selectedServices[]`
  - `first_name`, `last_name`, `father_name`
  - `birth_date[]`, `status[]`
  - `pin`, `ticket_id`, `staff_name`
  - `enteredText`, `pg_size`, `pg_num`
- Response: `{data: [...], count: N}`

#### 5.2.3. Müştəri API

**GET /api/customers/**

- Müştəri siyahısı
- Query parametrləri:
  - `selectedBranches[]`, `enteredText`
  - `customer_id`, `minCreatedAtSelected`, `maxCreatedAtSelected`
  - `first_name`, `last_name`, `father_name`
  - `pin`, `customsnumber`, `name`
  - `minDateSelected`, `maxDateSelected`
  - `pg_size`, `pg_num`
- Response: `{data: [...], count: N}`

**GET /api/customers/{customer_id}/visits/**

- Müəyyən müştəri üçün visit siyahısı
- Query parametrləri: tarix, branch, service filterləri
- Response: `{data: [...], count: N, profile: {...}}`

#### 5.2.4. Visit API

**GET /api/visits/{visit_id}/transactions/**

- Müəyyən visit üçün transaksiya siyahısı
- Response: `{data: [...], visit_data: {...}, profile_data: {...}, declarations: [...], count: N}`

#### 5.2.5. Export API

**GET /api/export/?data_url={type}**

- Excel export
- `data_url` dəyərləri:
  - `report` - Statistika hesabatı
  - `customer-list` - Müştəri siyahısı
  - `visit-list-customer` - Visit siyahısı
  - `visit-transaction` - Transaksiya siyahısı
- Response: `{url: "http://host/stmedia/output-YYYY-MM-DDTHH-MM-SS.xlsx"}`

#### 5.2.6. Risk FIN API

**POST /api/risk-fin/**

- Risk FIN əlavə et və ya yenilə
- Request: `{fin, is_risk, note}`
- Həm stat, həm də qp_agent database-ə yazır

#### 5.2.7. Audio Recording API

**GET /api/audio-recording/?date=YYYY-MM-DD&transaction_id=XXX**

- Samba serverdən OPUS faylını gətirir
- Response: OPUS audio file (audio/ogg)
- Content-Disposition: inline

### 5.3. MRZ Passport Reading (mrz_input.py)

**Funksiyalar:**

```python
def get_id_data(input_string):
    # MRZ kodunu parse edir
    # TD1, TD2, TD3 formatlarını dəstəkləyir
    # Returns: fields object (optional_data=FIN, birth_date)
```

**İstifadə:**

- `mrz` library (TD1CodeChecker, TD2CodeChecker, TD3CodeChecker)
- 90, 72, 88 simvol uzunluğunda kodlar

### 5.4. Hospital Service Integration

**SOAP API:**

- Endpoint: `http://192.168.253.10:81/HospitalService.asmx`
- Method: `GetPersonByPinAndBirthdate`
- Auth: `CustomsHospital` / `CsHp!@#321Qwer`
- Response: XML (person məlumatları)

**Development mode:**

- `USE_POST_XML=True` olduqda mock XML response istifadə olunur

### 5.5. Samba File Access

**smbprotocol library:**

- Samba serverdən fayl oxuma
- Connection → Session → TreeConnect → Open → Read

**Fayl yolu:**

```
recordings/YYYY-MM-DD/transaction_id.opus
```

### 5.6. Excel Export

**pandas + openpyxl:**

- DataFrame yaradılır
- Excel formatına export edilir
- Media klasöründə saxlanılır
- URL qaytarılır: `/stmedia/output-YYYY-MM-DDTHH-MM-SS.xlsx`

### 5.7. Deployment

**uWSGI:**

```bash
uwsgi --ini uwsgi.ini
```

**Docker:**

```bash
docker-compose up
```

---

## 6. API Dokumentasiyası

### 6.1. Customs Project API

**Swagger/OpenAPI:**

- URL: `/api/schema/swagger-ui/`
- drf-spectacular istifadə olunur

**Əsas endpoint qrupları:**

1. Visit management
2. Declaration management
3. Note management
4. Permission management
5. Schedule Group management
6. Service permissions
7. Active recordings
8. Excel export

### 6.2. Customs Statistics API

**API struktur:**

- RESTful design
- Query parameter filtering
- Pagination support
- Excel export

---

## 7. Deployment

### 7.1. Local Agent Deployment

**Windows quraşdırma:**

1. `dist/local_agent/local_agent.exe` kopyala
2. `.env` faylını yarat
3. `config/` klasörünü kopyala
4. `tools/ffmpeg.exe` kopyala
5. Exe-ni işə sal

**Auto-start:**

- Windows Task Scheduler istifadə edilə bilər
- Startup folder-ə qoyula bilər

### 7.2. Django Projects Deployment

**Gunicorn:**

```bash
gunicorn customs_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120
```

**Nginx reverse proxy:**

```nginx
server {
    listen 80;
    server_name api.example.com;
  
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
  
    location /media/ {
        alias /path/to/media/;
    }
}
```

**Docker:**

```bash
docker-compose up -d
```


## 8. Troubleshooting

### 8.1. Local Agent Problemləri

**Mikrofon tapılmır:**

- Device index-i yoxla (`config/config.json`)
- Mikrofonun qoşulu olduğunu yoxla
- PyAudio quraşdırılmışdır?

**Recording başlamır:**

- Permission yoxlanılır? (branch_id, user_id)
- Database bağlantısı işləyir?
- Log fayllarını yoxla

**Upload uğursuz:**

- Samba credentials düzgündür?
- Network bağlantısı var?
- Samba server əlçatandır?
- Upload queue statusunu yoxla

**OPUS conversion uğursuz:**

- `tools/ffmpeg.exe` mövcuddur?
- Disk space kifayətdir?
- WAV faylı düzgün yaranıb?

### 8.2. Django API Problemləri

**Database bağlantı xətası:**

- Environment variables düzgündür?
- PostgreSQL işləyir?
- Network bağlantısı var?

**CORS xətası:**

- `CORS_ALLOW_ALL_ORIGINS = True` (development)
- Production-da konkret origin-lər təyin et

**API response yavaş:**

- Stat database asinxron yazma işləyir?
- Database index-lər mövcuddur?
- Query optimization lazımdır?

### 8.3. Samba Server Problemləri

**Fayl tapılmır:**

- Fayl yolu düzgündür? (`recordings/YYYY-MM-DD/transaction_id.opus`)
- Samba credentials düzgündür?
- Share adı düzgündür?

**Bağlantı xətası:**

- Server IP düzgündür?
- Port 445 açıqdır?
- Firewall qaydaları?

---

## 9. Performans Optimizasiyası

### 9.1. Database Optimizasiya

**Index-lər:**

- `visit_id`, `transaction_id` üzrə index-lər
- `branch_id`, `user_id` üzrə index-lər
- `customs_number` üzrə index

**Query optimizasiya:**

- JOIN-ləri optimallaşdır
- Pagination istifadə et
- Lazy loading

### 9.2. Asinxron Əməliyyatlar

**Stat database yazma:**

- Threading.Thread istifadə olunur
- Ana əməliyyatları yavaşlatmır

**Upload prosesi:**

- Background thread
- Queue sistemi
- Retry mexanizmi

### 9.3. Caching

**Mümkün cache strategiyaları:**

- Redis (branch, service list-ləri)
- Django cache framework
- API response caching

---

## 10. Təhlükəsizlik

### 10.1. Authentication/Authorization

**Hazırkı vəziyyət:**

- API authentication yoxdur (açıq API)
- Production-da authentication əlavə edilməlidir

**Təklif edilən:**

- JWT token authentication
- API key authentication
- OAuth2

### 10.2. Data Protection

**Sensitive data:**

- Database credentials (.env)
- Samba credentials (JSON file)
- Encryption key

**Təhlükəsizlik tədbirləri:**

- .env faylını git-ə daxil etmə
- Production credentials ayrı saxla
- HTTPS istifadə et

### 10.3. Input Validation

**DRF Serializers:**

- Field validation
- Type checking
- Required fields

**SQL Injection:**

- Parameterized queries istifadə olunur
- Raw SQL-də parametrlər istifadə olunur

---

## 11. Monitoring və Logging

### 11.1. Logging

**Local Agent:**

- Console output

**Django:**

- Django logging framework
- Console handler
- File handler (production)

### 11.2. Monitoring

**Mümkün monitoring:**

- Database connection status
- Upload queue status
- Active recordings count
- API response time
- Error rate

---

---

**Son yeniləmə:** 2025-01-XX
**Versiya:** 1.0
**Müəllif:** Development Team
