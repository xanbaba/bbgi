# Gömrük Xidmətləri İdarəetmə Sistemi - Biznes Dokümantasiyası

## 1. Sistem Haqqında

Gömrük Xidmətləri İdarəetmə Sistemi müştəri ziyarətlərinin idarə edilməsi, səs yazılarının qeydə alınması və statistika hesabatlarının hazırlanması üçün yaradılmış inteqrasiya edilmiş sistemdir.

Sistem 3 əsas komponentdən ibarətdir:

- **Local Agent** - Windows agent proqramı (səs yazma və yükləmə)
- **Customs Project** - Visit idarəetmə API-sı
- **Customs Statistics** - Statistika və hesabatlar API-sı

---

## 2. Sistem Komponentləri

### 2.1. Local Agent (Windows Agent)

**Məqsəd:** Operatorların iş stolunda quraşdırılan Windows agent proqramıdır. Müştəri ilə operator arasında olan söhbəti avtomatik qeydə alır və mərkəzi serverə yükləyir.

**Əsas Funksiyalar:**

- Mikrofon vasitəsilə səs yazma
- Səs fayllarını OPUS formatına çevirmə
- Samba serverə avtomatik yükləmə
- Mikrofon ayrılma/reconnect idarəetməsi
- Recording icazələrinin yoxlanılması

**İstifadəçilər:** Operatorlar (hər iş stolunda quraşdırılır)

---

### 2.2. Customs Project (Visit İdarəetmə API)

**Məqsəd:** Müştəri ziyarətlərinin, bəyannamələrin və qeydlərin idarə edilməsi üçün REST API xidmətidir.

**Əsas Funksiyalar:**

- Visit yaradılması və yenilənməsi
- Declaration (bəyannamə) əlavə edilməsi
- Note (qeyd) əlavə edilməsi
- Visit şəkilinin saxlanması
- Recording icazələrinin idarə edilməsi (branch və user səviyyəsində)
- Schedule Group idarəetməsi
- Service Auto-End və Accept Permission idarəetməsi
- Aktiv recording-ların izlənməsi

**İstifadəçilər:** Frontend tətbiqləri, digər sistemlər (API istifadəçiləri)

---

### 2.3. Customs Statistics (Statistika və Hesabatlar API)

**Məqsəd:** Ziyarətlər, müştərilər və transaksiyalar üzrə statistika hesabatlarının hazırlanması və Excel formatında export edilməsi.

**Əsas Funksiyalar:**

- Pasport MRZ kodunun oxunması və müştəri məlumatlarının alınması
- Statistika hesabatlarının hazırlanması
- Müştəri siyahılarının göstərilməsi
- Visit siyahılarının göstərilməsi
- Transaksiya siyahılarının göstərilməsi
- Excel formatında export
- Risk FIN kodlarının idarə edilməsi
- Səs yazılarının (OPUS) Samba serverdən götürülməsi

**İstifadəçilər:** İdarəçilər, analitiklər, hesabat istifadəçiləri

---

## 3. İş Axını (Workflow)

### 3.1. Visit Yaradılması və Səs Yazma Prosesi

```
1. Müştəri gəlir və visit yaradılır
   ↓
2. Customs Project API-sına visit məlumatları göndərilir
   ↓
3. Əgər branch və user üçün recording icazəsi varsa:
   ↓
4. Local Agent-a recording başlatma əmri göndərilir
   ↓
5. Local Agent mikrofonu aktivləşdirir və səs yazma başlayır
   ↓
6. Operator müştəri ilə söhbət edir (səs avtomatik qeydə alınır)
   ↓
7. Visit bitdikdə recording dayandırılır
   ↓
8. Local Agent səs faylını OPUS formatına çevirir
   ↓
9. OPUS faylı Samba serverə yüklənir (recordings/YYYY-MM-DD/transaction_id.opus)
   ↓
10. Database-də recording log yaradılır
```

### 3.2. Declaration və Note Əlavə Etmə Prosesi

```
1. Operator visit zamanı declaration (bəyannamə) məlumatlarını daxil edir
   ↓
2. Customs Project API-sına declaration göndərilir
   ↓
3. Declaration database-ə yazılır (həm ana, həm də stat database-ə)
   ↓
4. Operator lazım olduqda note (qeyd) əlavə edir
   ↓
5. Note database-ə yazılır
```

### 3.3. Statistika və Hesabat Prosesi

```
1. İdarəçi Customs Statistics API-sına sorğu göndərir
   ↓
2. API stat database-dən məlumatları çəkir
   ↓
3. Məlumatlar filter edilir (tarix, branch, service və s.)
   ↓
4. Nəticələr Excel formatında export edilir
   ↓
5. İdarəçi Excel faylını yükləyir
```

---

## 4. Əsas Biznes Funksiyaları

### 4.1. Visit İdarəetməsi

**Visit nədir?**
Visit müştərinin gömrük xidməti üçün gəldiyi ziyarətdir. Hər visit-də:

- Müştəri məlumatları (ad, soyad, FIN, doğum tarixi, telefon, şəkil)
- Branch ID (filial)
- Service ID (xidmət növü)
- Declaration-lar (bəyannamələr)
- Note-lar (qeydlər)

**Visit yaradılması:**

- Yeni visit yaradılanda müştəri məlumatları daxil edilir
- Şəkil base64 formatında göndərilir və fayl kimi saxlanılır
- Visit ID unikal identifikator kimi istifadə olunur

**Visit yenilənməsi:**

- Müştəri məlumatları yenilənə bilər
- Şəkil yenilənə bilər

---

### 4.2. Declaration (Bəyannamə) İdarəetməsi

**Declaration nədir?**
Declaration müştərinin gömrük bəyannaməsidir. Hər declaration-da:

- Customs Number (gömrük nömrəsi)
- Type (növ)
- Representative məlumatları (nümayəndə)
- Company məlumatları (şirkət)

**Declaration əməliyyatları:**

- Yeni declaration əlavə edilə bilər
- Mövcud declaration yenilənə bilər
- Declaration silinə bilər
- Eyni customs_number olan visitlər tapıla bilər

---

### 4.3. Note (Qeyd) İdarəetməsi

**Note nədir?**
Note operatorun visit zamanı etdiyi qeyddir. Hər note-da:

- Content (məzmun)
- Status (1 = təmin edildi, 0 = təmin edilmədi)
- Action (hərəkət növü: "finish", "call" və s.)
- Table (cədvəl adı)

**Note əməliyyatları:**

- Visit-ə yeni note əlavə edilə bilər
- Note-lar tarixə görə sıralanır

---

### 4.4. Səs Yazma (Recording) İdarəetməsi

**Recording nədir?**
Recording operator ilə müştəri arasında olan söhbətin səs yazısıdır.

**Recording prosesi:**

1. Visit başlayanda recording avtomatik başlayır (əgər icazə varsa)
2. Səs WAV formatında qeydə alınır
3. Recording bitdikdə WAV → OPUS formatına çevrilir
4. OPUS faylı Samba serverə yüklənir
5. Database-də recording log yaradılır

**Recording icazələri:**

- Branch səviyyəsində: Bütün branch üçün recording aktiv/deaktiv edilə bilər
- User səviyyəsində: Konkret user üçün recording aktiv/deaktiv edilə bilər
- Default: İcazə yoxdursa, recording aktivdir

**Mikrofon idarəetməsi:**

- Mikrofon ayrıldıqda sistem avtomatik aşkar edir
- Mikrofon geri qoşulduqda recording davam edir
- Mikrofon statusu database-də qeydə alınır

---

### 4.5. Schedule Group İdarəetməsi

**Schedule Group nədir?**
Schedule Group müəyyən müddət üçün aktiv olan xidmət qrupudur. Hər il yeni group yaradılır və müəyyən müddət aktiv qalır.

**Schedule Group əməliyyatları:**

- Yeni group yaradılır (ad, lifetime, unit: Year/Month/Day)
- Group-a servislər əlavə edilir
- Group yenilənir və ya silinir

---

### 4.6. Service Auto-End və Accept Permission

**Service Auto-End:**

- Müəyyən service və branch kombinasiyası üçün visit avtomatik bitirilə bilər
- External API vasitəsilə visit avtomatik olaraq service point-ə əlavə edilir və bitirilir

**Service Accept Permission:**

- Müəyyən service və branch kombinasiyası üçün visit qəbul edilə bilər və ya edilməz
- `is_accept=true` olan visitlər filter edilə bilər

---

### 4.7. Statistika və Hesabatlar

**Statistika növləri:**

- Visit statistika (tarix, branch, service, müştəri məlumatları)
- Müştəri siyahısı (bütün müştərilər, visit sayı ilə)
- Visit siyahısı (müəyyən müştəri üçün)
- Transaksiya siyahısı (müəyyən visit üçün)

**Filter seçimləri:**

- Tarix aralığı
- Branch seçimi
- Service seçimi
- Müştəri məlumatları (ad, soyad, FIN)
- Status seçimi

**Export:**

- Bütün hesabatlar Excel formatında export edilir
- Excel faylları media klasöründə saxlanılır

---

### 4.8. Risk FIN İdarəetməsi

**Risk FIN nədir?**
Risk FIN müəyyən FIN kodunun riskli olduğunu göstərir.

**Risk FIN əməliyyatları:**

- Yeni risk FIN əlavə edilir (FIN, is_risk=true/false, note)
- Risk FIN yenilənir
- Risk FIN-lər visit və müştəri siyahılarında göstərilir

---

## 5. İstifadəçi Rolları və İcazələr

### 5.1. Operator

- Visit yaradır və yeniləyir
- Declaration və note əlavə edir
- Səs yazma avtomatik başlayır (icazə varsa)

### 5.2. İdarəçi

- Bütün visitləri görür
- Statistika hesabatlarını hazırlayır
- Recording icazələrini idarə edir
- Schedule Group idarə edir
- Risk FIN idarə edir

### 5.3. Sistem Administratoru

- Sistem konfiqurasiyasını idarə edir
- Database idarə edir
- Local Agent quraşdırır və konfiqurasiya edir

---

## 6. Database Struktur

Sistem 3 əsas database istifadə edir:

1. **qp_agent** - Ana database (visit, declaration, note, permission)
2. **stat** - Statistika database (fact və dim cədvəlləri)
3. **Local SQLite** - Local Agent üçün (recording log, upload queue)

**Sinxronizasiya:**

- Visit, declaration, note məlumatları həm ana, həm də stat database-ə yazılır
- Stat database-ə yazma asinxron olaraq baş verir (performans üçün)

---

## 7. Samba Server

**Məqsəd:** Səs yazılarının (OPUS fayllarının) saxlanması

**Struktur:**

```
recordings/
  └── YYYY-MM-DD/
      ├── transaction_id_1.opus
      ├── transaction_id_2.opus
      └── ...
```

**Yükləmə prosesi:**

1. Local Agent OPUS faylını yaradır
2. Samba serverə yükləyir (günlük folder strukturunda)
3. Yükləmə uğurlu olduqdan sonra lokal fayl silinir

---

## 8. Sistem İnteqrasiyaları

### 8.1. External API (Qmatic)

- Visit avtomatik bitirilməsi üçün istifadə olunur
- Service Auto-End aktiv olduqda visit avtomatik olaraq service point-ə əlavə edilir və bitirilir

### 8.2. Hospital Service (SOAP)

- Pasport MRZ kodundan müştəri məlumatlarının alınması
- FIN və doğum tarixinə görə müştəri məlumatları gətirilir

---

## 9. Üstünlüklər

1. **Avtomatik səs yazma** - Operator işini pozmadan səs avtomatik qeydə alınır
2. **Mərkəzi idarəetmə** - Bütün visitlər mərkəzi database-də saxlanılır
3. **Detallı statistika** - Çoxlu filter seçimləri ilə hesabatlar
4. **Risk idarəetməsi** - Risk FIN kodları ilə xüsusi müştərilər izlənilir
5. **İcazə idarəetməsi** - Branch və user səviyyəsində recording icazələri
6. **Excel export** - Bütün hesabatlar Excel formatında export edilir

---

## 10. Texniki Dəstək

Texniki suallar və problemlər üçün:

- Log fayllarını yoxlayın
- Database bağlantılarını yoxlayın
- Samba server bağlantısını yoxlayın

---
