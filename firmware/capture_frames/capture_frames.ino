/*
 * ESP32-CAM frame collector for the drowsiness detector (fast capture + ZIP download)
 * ---------------------------------------------------------------------------------
 * The ESP32-CAM opens its own Wi-Fi hotspot; open http://192.168.4.1 in a laptop browser:
 *   1. Press "Rekam FOKUS" (record alert) or "Rekam KANTUK" (record drowsy): frames are
 *      captured continuously and kept in the browser.
 *   2. Press "Stop".
 *   3. Press "Unduh ZIP" (download ZIP): all frames are saved in one ZIP file named
 *      fokus.0001.<time>.jpg / kantuk.0001.<time>.jpg
 * The label in the file name is read by Edge Impulse ("Infer label from filename")
 * and by device_test/send_images.py. The web page text is in Indonesian.
 *
 * Camera settings are the SAME as in the inference sketch (QVGA 320x240, JPEG),
 * so collected frames match what the device sees in use.
 * This sketch was used to capture the 382 pilot frames (Table VI).
 *
 * Board: AI Thinker ESP32-CAM, PSRAM: Enabled, ESP32 core 2.0.17
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ---------- Hotspot ESP32-CAM ----------
const char *AP_SSID = "ESP32CAM-Dataset";
const char *AP_PASS = "kantuk123";   // at least 8 characters

// ---------- AI Thinker camera pins ----------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t server = NULL;

// ---------- Web page ----------
static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dataset Kantuk ESP32-CAM</title>
<style>
 body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:16px;text-align:center}
 h1{font-size:1.2rem;margin:4px 0 12px}
 img{width:100%;max-width:480px;border-radius:8px;background:#222}
 .row{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:10px 0}
 button,select{font-size:1rem;padding:11px 14px;border:0;border-radius:8px;cursor:pointer;color:#fff}
 select{background:#333}
 .f{background:#1f8f4e}.k{background:#c0392b}.g{background:#555}.b{background:#2d6cdf}
 button:disabled{opacity:.45;cursor:default}
 .cnt{font-size:1.15rem;margin:8px}
 #st{min-height:1.3em;color:#f1c40f}
 #rec{display:none;color:#ff5c5c;font-weight:700}
 small{color:#aaa}
</style></head><body>
<h1>Pengambil Dataset Kantuk (rekam cepat)</h1>
<img id="prev" alt="preview kamera">
<div id="rec">&#9679; MEREKAM <span id="recl"></span></div>
<div class="cnt">Fokus: <b id="cf">0</b> &nbsp;|&nbsp; Kantuk: <b id="ck">0</b> &nbsp;|&nbsp; Total: <b id="ct">0</b> (<span id="mb">0</span> MB)</div>
<div class="row">
 <button class="f" id="bf" onclick="mulai('fokus')">Rekam FOKUS</button>
 <button class="k" id="bk" onclick="mulai('kantuk')">Rekam KANTUK</button>
 <button class="g" id="bs" onclick="stop()" disabled>Stop</button>
 <select id="iv" title="jeda antar foto">
  <option value="200">tiap 0,2 dtk</option>
  <option value="400" selected>tiap 0,4 dtk</option>
  <option value="700">tiap 0,7 dtk</option>
  <option value="1000">tiap 1 dtk</option>
 </select>
</div>
<div class="row">
 <button class="b" id="bz" onclick="unduh()">Unduh ZIP</button>
 <button class="g" onclick="batal(10)">Batalkan 10 terakhir</button>
 <button class="g" onclick="hapus()">Hapus semua</button>
</div>
<div id="st"></div>
<small>Foto ditampung di browser dan baru tersimpan saat "Unduh ZIP". Jangan tutup/refresh halaman sebelum mengunduh.<br>
Pintasan: F = rekam fokus, K = rekam kantuk, spasi = stop.</small>
<script>
const img=document.getElementById('prev'), st=document.getElementById('st');
let foto=[], merekam=null, sibuk=false, nomor={fokus:0,kantuk:0};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function tampil(){
 const f=foto.filter(x=>x.label==='fokus').length, k=foto.length-f;
 document.getElementById('cf').textContent=f; document.getElementById('ck').textContent=k;
 document.getElementById('ct').textContent=foto.length;
 document.getElementById('mb').textContent=(foto.reduce((s,x)=>s+x.data.length,0)/1048576).toFixed(1);
 const r=!!merekam;
 document.getElementById('bf').disabled=r; document.getElementById('bk').disabled=r;
 document.getElementById('bs').disabled=!r; document.getElementById('bz').disabled=r||!foto.length;
 document.getElementById('rec').style.display=r?'block':'none';
 document.getElementById('recl').textContent=r?merekam.toUpperCase():'';
}
async function ambil(){
 const r=await fetch('/capture?t='+Date.now(),{cache:'no-store'});
 if(!r.ok) throw new Error('gagal');
 return new Uint8Array(await r.arrayBuffer());
}
function lihat(data){
 const u=URL.createObjectURL(new Blob([data],{type:'image/jpeg'}));
 img.onload=()=>URL.revokeObjectURL(u); img.src=u;
}
async function preview(){
 while(true){
  if(!merekam && !sibuk){ try{ lihat(await ambil()); }catch(e){ st.textContent='Kamera tidak merespons...'; } }
  await sleep(merekam?500:300);
 }
}
async function mulai(label){
 if(merekam) return;
 merekam=label; tampil(); st.textContent='Merekam '+label+'...';
 while(merekam===label){
  const t0=Date.now();
  try{
   sibuk=true; const d=await ambil(); sibuk=false;
   nomor[label]++;
   foto.push({label, name:label+'.'+String(nomor[label]).padStart(4,'0')+'.'+Date.now()+'.jpg', data:d});
   lihat(d); tampil();
  }catch(e){ sibuk=false; st.textContent='Satu foto gagal, lanjut...'; }
  const jeda=+document.getElementById('iv').value-(Date.now()-t0);
  if(jeda>0) await sleep(jeda);
 }
}
function stop(){ if(merekam){ st.textContent='Berhenti. '+foto.length+' foto di memori, belum diunduh.'; merekam=null; tampil(); } }
function batal(n){ if(merekam) return; const k=Math.min(n,foto.length); foto.splice(foto.length-k,k); st.textContent=k+' foto terakhir dibatalkan.'; tampil(); }
function hapus(){ if(merekam||!foto.length) return; if(confirm('Hapus semua '+foto.length+' foto dari memori?')){ foto=[]; nomor={fokus:0,kantuk:0}; st.textContent='Semua foto dihapus.'; tampil(); } }

// --- Minimal ZIP writer (no compression, no internet/CDN needed) ---
const CRC=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0;}return t;})();
function crc32(u){let c=0xFFFFFFFF;for(let i=0;i<u.length;i++)c=CRC[(c^u[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
function buatZip(files){
 const enc=new TextEncoder(), isi=[], pusat=[]; let off=0;
 for(const f of files){
  const nm=enc.encode(f.name), crc=crc32(f.data), sz=f.data.length;
  const h=new DataView(new ArrayBuffer(30));
  h.setUint32(0,0x04034b50,true); h.setUint16(4,20,true); h.setUint16(12,0x21,true);
  h.setUint32(14,crc,true); h.setUint32(18,sz,true); h.setUint32(22,sz,true); h.setUint16(26,nm.length,true);
  isi.push(new Uint8Array(h.buffer),nm,f.data);
  const c=new DataView(new ArrayBuffer(46));
  c.setUint32(0,0x02014b50,true); c.setUint16(4,20,true); c.setUint16(6,20,true); c.setUint16(14,0x21,true);
  c.setUint32(16,crc,true); c.setUint32(20,sz,true); c.setUint32(24,sz,true); c.setUint16(28,nm.length,true); c.setUint32(42,off,true);
  pusat.push(new Uint8Array(c.buffer),nm);
  off+=30+nm.length+sz;
 }
 const csz=pusat.reduce((s,p)=>s+p.length,0);
 const e=new DataView(new ArrayBuffer(22));
 e.setUint32(0,0x06054b50,true); e.setUint16(8,files.length,true); e.setUint16(10,files.length,true);
 e.setUint32(12,csz,true); e.setUint32(16,off,true);
 return new Blob([...isi,...pusat,new Uint8Array(e.buffer)],{type:'application/zip'});
}
function unduh(){
 if(merekam||!foto.length) return;
 const zip=buatZip(foto), a=document.createElement('a');
 const w=new Date(), p=n=>String(n).padStart(2,'0');
 a.href=URL.createObjectURL(zip);
 a.download='dataset_kantuk_'+w.getFullYear()+p(w.getMonth()+1)+p(w.getDate())+'_'+p(w.getHours())+p(w.getMinutes())+'.zip';
 document.body.appendChild(a); a.click(); a.remove();
 setTimeout(()=>URL.revokeObjectURL(a.href),5000);
 st.textContent='ZIP diunduh: '+foto.length+' foto. Setelah file tersimpan, tekan "Hapus semua" untuk sesi baru.';
}
document.addEventListener('keydown',e=>{
 const k=e.key.toLowerCase();
 if(k==='f') mulai('fokus'); else if(k==='k') mulai('kantuk'); else if(k===' '){ e.preventDefault(); stop(); }
});
window.addEventListener('beforeunload',e=>{ if(foto.length){ e.preventDefault(); e.returnValue=''; } });
tampil(); preview();
</script></body></html>
)rawliteral";

// ---------- Handler HTTP ----------
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Gagal mengambil frame");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

void startServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  httpd_uri_t index_uri   = { .uri = "/",        .method = HTTP_GET, .handler = index_handler,   .user_ctx = NULL };
  httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = capture_handler, .user_ctx = NULL };
  if (httpd_start(&server, &config) == ESP_OK) {
    httpd_register_uri_handler(server, &index_uri);
    httpd_register_uri_handler(server, &capture_uri);
  }
}

// ---------- Setup ----------
void setup() {
  Serial.begin(115200);
  Serial.println();

  camera_config_t config = {};
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href  = HREF_GPIO_NUM;
  config.pin_pclk  = PCLK_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.ledc_timer   = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.pixel_format = PIXFORMAT_JPEG;   // same as the inference sketch
  config.frame_size   = FRAMESIZE_QVGA;   // 320x240, same as the inference sketch
  config.jpeg_quality = 12;
  config.fb_count     = 2;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST; // always take the latest frame

  if (!psramFound()) {
    Serial.println("PSRAM tidak terdeteksi! Aktifkan PSRAM di menu Tools.");
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Inisialisasi kamera gagal: 0x%x\n", err);
    while (true) delay(1000);
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  startServer();

  Serial.println("=== Pengambil Dataset Siap ===");
  Serial.printf("1. Sambungkan laptop ke WiFi: %s (password: %s)\n", AP_SSID, AP_PASS);
  Serial.print("2. Buka browser ke: http://");
  Serial.println(WiFi.softAPIP());
}

void loop() {
  delay(1000);
}
