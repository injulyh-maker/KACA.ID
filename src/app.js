const fullscreenButton=document.getElementById('fullscreenToggle');
function updateFullscreenButton(active){if(!fullscreenButton)return;fullscreenButton.classList.toggle('active',Boolean(active));fullscreenButton.setAttribute('aria-label',active?'Keluar dari layar penuh':'Masuk mode layar penuh');fullscreenButton.title=active?'Keluar dari layar penuh (Esc)':'Layar penuh (F11)';const label=fullscreenButton.querySelector('.fullscreen-label');if(label)label.textContent=active?'Keluar layar penuh':'Layar penuh';}
if(fullscreenButton){fullscreenButton.addEventListener('click',async()=>{try{const active=await window.kaca.toggleFullscreen();updateFullscreenButton(active);}catch(e){console.error('Gagal mengubah mode layar penuh:',e);}});window.kaca.isFullscreen().then(updateFullscreenButton).catch(()=>{});window.kaca.onFullscreenChange(updateFullscreenButton);}
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let settings={};

let baseSettings={},eventStore={activeEventId:null,events:[]};
const eventConfigKeys=['paperSize','orientation','customWidth','customHeight','printCopies','additionalPrintEnabled','additionalPrintMaxCopies','autoPrintEnabled','printDpi','printBorderless','printerDriverPaper','frameId','frameSlots','layoutSlots','frameLayouts','driveQrEnabled','driveQrLayout','driveQrLayouts','enablePhotoMode','enableVideoMode','livePhotoEnabled','livePhotoDuration','videoQuality','videoDurationSeconds','defaultFilter','sessionMode','sessionDurationMinutes'];
const activeEvent=()=>eventStore.events.find(e=>e.id===eventStore.activeEventId)||null;
const effectiveSettings=()=>({...baseSettings,...(activeEvent()?.config||{})});
const frameBelongsToCurrentEvent=f=>String(f?.event_id||'')===String(activeEvent()?.id||'');
async function saveScopedSettings(){
 const ev=activeEvent();
 if(ev){
   const general={...settings};
   for(const key of eventConfigKeys){ev.config[key]=settings[key]; if(Object.prototype.hasOwnProperty.call(baseSettings,key))general[key]=baseSettings[key];else delete general[key];}
   await window.kaca.writeEvents(eventStore);
   baseSettings={...general};
   await window.kaca.writeSettings(baseSettings);
 }else{baseSettings={...settings};await window.kaca.writeSettings(baseSettings);}
}
async function activateEvent(id){
 if(id!==null&&!eventStore.events.some(e=>e.id===id))throw new Error('Event tidak ditemukan.');
 eventStore.activeEventId=id;
 await window.kaca.writeEvents(eventStore);
 settings=effectiveSettings();applyAppTheme();await go('dashboard');
}

const titles={events:'Manajemen Event',dashboard:'Dashboard',videoCapture:'Video Studio',setup:'Setup Wizard',capture:'Capture Studio',sessionSettings:'Pengaturan Sesi',generalSettings:'Pengaturan Umum',frames:'Frame & Layout',filters:'Filter Foto',output:'Output & Cetak',archive:'Arsip Sesi',voucher:'Voucher',payment:'Pembayaran',devices:'Pengaturan Perangkat',printers:'Printer & Kertas',appearance:'Tampilan & Tema',license:'Lisensi KACA.ID',cloudControl:'Cloud Control'};
const descriptions={videoCapture:'Mode perekaman video, pratinjau hasil, dan berbagi file.',setup:'Panduan konfigurasi awal booth dan perangkat.',capture:'Countdown, sesi pemotretan, retake, dan penyimpanan foto.',sessionSettings:'Pilih sistem kesempatan foto: berdasarkan jumlah slot frame atau durasi sesi.',generalSettings:'Atur kualitas foto, video, DPI cetak, dan kamera.',frames:'Kelola ukuran hasil, jumlah slot, dan komposisi cetak.',filters:'Pilih tampilan foto yang diterapkan saat pengambilan.',output:'Lihat hasil sesi, simpan file digital, dan cetak melalui dialog Windows.',archive:'Riwayat sesi foto yang tersimpan secara lokal.',voucher:'Buat dan kelola voucher sesi KACA.ID.',payment:'Konfigurasi metode pembayaran dan nominal transaksi.',devices:'Kelola kamera, printer, dan perangkat eksternal.',printers:'Pilih printer Windows dan simpan ukuran kertas cetak.',appearance:'Atur warna, logo, tipografi, dan tampilan booth.',license:'Aktivasi dan status lisensi aplikasi KACA.ID.'};
function dashboard(){
 const photos=settings.dashboardPhotos||[];
 const bg=settings.dashboardVideo||'';
 const background=settings.dashboardBackgroundDisabled?'':(settings.dashboardImage?`<img class="dash-background-image" src="${settings.dashboardImage}" alt="Latar dasbor">`:bg?`<video class="dash-background" autoplay muted loop playsinline><source src="${bg}" type="${bg.toLowerCase().endsWith('.webm')?'video/webm':'video/mp4'}"></video>`:'');
 const logo=settings.dashboardLogo||'';
 const title=settings.dashboardTitle||'KACA Studio';
 const galleryItems=photos.length?Array.from({length:Math.max(5,photos.length)},(_,i)=>photos[i%photos.length]):[];
 const gallery=galleryItems.map(p=>`<div class="dash-photo"><img src="${p.url}" alt="${esc(p.name||'Foto galeri')}"></div>`).join('');
 const rolling=photos.length?gallery+gallery:'<div class="dash-gallery-empty">Tambahkan foto contoh melalui Pengaturan Tampilan Dasbor</div>';
 return `<div class="studio-dashboard" style="--dash-accent:${settings.dashboardAccent||'#D23A2B'};--dash-surface:${settings.dashboardSurface||'#FFFFFF'};--dash-ink:${settings.dashboardInk||'#171717'}">
 ${background}<div class="dash-shade"></div>
 <button class="dash-home" id="adminHome" aria-label="Pengaturan Admin" title="Pengaturan Admin">⌂</button>
 <div class="dash-content"><div class="dash-brand" data-ui-part="brand"><h1>${esc(title)}</h1></div>${logo?`<img class="dash-logo dash-corner-logo" src="${logo}" alt="Logo dasbor">`:''}
 ${activeEvent()?`<div class="active-event-banner">EVENT AKTIF · ${esc(activeEvent().name)} · ${esc(activeEvent().date||'Tanpa tanggal')}</div>`:''}<section class="dash-camera-card" data-ui-part="preview"><div class="dash-camera-window"><img id="dashLivePreview" alt="Preview kamera live" style="display:none"><div class="dash-camera-placeholder" id="dashCameraPlaceholder"><span>◉</span><b>Menunggu kamera</b><small>Preview akan tampil saat kamera terdeteksi</small></div><span class="dash-camera-state" id="dashCameraState">MEMERIKSA KAMERA</span></div>
 <div class="dash-mode-actions" data-ui-part="actions">${settings.enablePhotoMode!==false?`<button class="dash-start" id="startPhotoSession"><span class="dash-mode-icon">📷</span><span>PHOTO</span></button>`:''}${settings.enableVideoMode!==false?`<button class="dash-start dash-video-start" id="startVideoSession"><span class="dash-mode-icon">🎥</span><span>VIDEO</span></button>`:''}</div></section></div>
 <section class="dash-gallery-section" data-ui-part="gallery"><div class="dash-gallery-track ${photos.length?'is-rolling':''}">${rolling}</div></section>
 </div>`;
}
async function renderAppearance(){
 const photos=settings.dashboardPhotos||[];
 $('#content').innerHTML=`<div class="panel dash-settings-panel"><div class="eyebrow2">KACA STUDIO / DASHBOARD</div><h3>Pengaturan Tampilan Dasbor</h3><p class="muted">Atur identitas, latar, warna, dan lima foto thumbnail yang tampil bergulir pada halaman awal.</p>
 <div class="form-grid">
 <div class="field"><label>Tulisan KACA Studio di Dashboard (bebas diedit)</label><input id="dashTitleInput" value="${(settings.dashboardTitle||'KACA Studio').replaceAll('"','&quot;')}"></div>
 <div class="field"><label>PIN Admin / Operator</label><input id="dashPinInput" type="password" inputmode="numeric" value="${(settings.adminPin||'1234').replaceAll('"','&quot;')}" placeholder="Minimal 4 digit"><small class="field-help">PIN awal: 1234. Segera ganti setelah instalasi.</small></div>
 <div class="field"><label>Warna tombol MULAI</label><input id="dashAccentInput" type="color" value="${settings.dashboardAccent||'#D23A2B'}"></div>
 <div class="field"><label>Warna panel preview</label><input id="dashSurfaceInput" type="color" value="${settings.dashboardSurface||'#FFFFFF'}"></div>
 <div class="field"><label>Warna teks judul</label><input id="dashInkInput" type="color" value="${settings.dashboardInk||'#171717'}"></div>
 <div class="field"><label>Tema area pengaturan</label><select id="dashThemeInput"><option value="dark">Gelap</option><option value="light">Terang</option></select></div></div>
 <div class="dash-settings-actions"><button class="btn secondary" id="chooseDashLogo">Pilih Logo Dasbor</button><span id="dashLogoName" class="muted">${esc(settings.dashboardLogoName||'Logo belum dipilih')}</span><button class="btn secondary" id="chooseDashVideo">Pilih Video Latar</button><span id="dashVideoName" class="muted">${esc(settings.dashboardVideoName||'Belum ada video latar, upload sendiri')}</span><button class="btn secondary" id="chooseDashImage">Pilih Foto Latar</button><span id="dashImageName" class="muted">${esc(settings.dashboardImageName||'Foto latar belum dipilih')}</span><button class="btn secondary" id="removeDashBackground">Hapus Latar Foto/Video</button><button class="btn secondary" id="restoreDashBackground">Gunakan Latar Bawaan</button></div>
 <div class="section-head"><h3>Galeri Thumbnail Dasbor</h3><span>${photos.length} foto dipilih · disarankan 5–15 foto</span></div>
 <div class="dash-gallery-manager">${photos.map((p,i)=>`<div class="dash-gallery-item"><img src="${p.url}" alt=""><span>${esc(p.name||'Foto '+(i+1))}</span><div><button data-photo-up="${i}" ${i===0?'disabled':''}>←</button><button data-photo-down="${i}" ${i===photos.length-1?'disabled':''}>→</button><button data-photo-remove="${i}" class="remove">Hapus</button></div></div>`).join('')||'<div class="empty">Belum ada foto galeri. Tambahkan foto yang ingin ditampilkan pada dasbor.</div>'}</div>
 <div class="actions"><button class="btn" id="addDashPhotos">＋ Tambahkan Foto</button><button class="btn" id="saveDashAppearance">Simpan Tampilan</button><button class="btn secondary" id="backDashboard">Kembali ke Dasbor</button></div><div class="notice" id="dashSettingsStatus">Foto akan ditampilkan dalam strip thumbnail bergerak di bagian bawah dasbor.</div></div>
 <div class="panel ui-designer-panel"><div class="eyebrow2">KACA STUDIO / ADVANCED UI DESIGNER</div><h3>Editor Visual Antarmuka</h3><p class="muted">Pilih tab layar, geser komponen langsung pada kanvas, dan tarik sudut kanan bawah untuk mengubah ukuran. Tidak perlu memasukkan angka posisi atau ukuran.</p><div class="ui-designer-tabs" id="uiDesignerTabs"><button class="active" data-ui-screen="dashboard">Dasbor</button><button data-ui-screen="preview">Preview Sesi</button><button data-ui-screen="frame">Pemilihan Frame</button><button data-ui-screen="filter">Filter</button><button data-ui-screen="result">Slide Hasil</button></div><div class="ui-designer-workspace"><div class="ui-designer-stage-wrap"><div class="ui-designer-stage" id="uiDesignerStage"></div><small class="field-help">Seret untuk memindahkan. Tarik handle sudut untuk mengubah ukuran.</small></div><aside class="ui-designer-inspector"><h4 id="uiDesignerSelectedTitle">Pilih komponen</h4><div class="field"><label>Warna komponen</label><input type="color" id="uiDesignerColor" value="#d8b56a"></div><div class="field"><label>Transparansi</label><input type="range" id="uiDesignerOpacity" min="10" max="100" value="100"></div><div class="field"><label>Ukuran</label><input type="range" id="uiDesignerScale" min="60" max="160" value="100"></div><button class="btn secondary" id="uiDesignerResetComponent">Reset Komponen</button></aside></div><div class="actions"><button class="btn" id="saveAdvancedTheme">Simpan Tema Visual</button><button class="btn secondary" id="resetAdvancedTheme">Pulihkan Semua Tema</button></div><div class="notice" id="advancedThemeStatus">Perubahan visual akan disimpan sebagai tema aplikasi.</div></div>`;
 $('#dashThemeInput').value=settings.dashboardTheme||'dark';
 // Display the actual selected fill color, not a thin outline.
 for(const id of ['dashAccentInput','dashSurfaceInput','dashInkInput','uiDesignerColor']){
   const input=$('#'+id);if(!input)continue;
   input.classList.add('kaca-visible-color-input');
   const chip=document.createElement('span');chip.className='kaca-color-preview';chip.title='Preview warna';
   input.insertAdjacentElement('afterend',chip);
   const update=()=>{chip.style.backgroundColor=input.value;chip.textContent=input.value.toUpperCase();};
   input.addEventListener('input',update);update();
 }
 const logoChooseButton=$('#chooseDashLogo');
 if(logoChooseButton){
   const remove=document.createElement('button');remove.type='button';remove.id='removeDashLogo';remove.className='btn secondary';remove.textContent='Hapus Logo Dasbor';
   logoChooseButton.insertAdjacentElement('afterend',remove);
   remove.onclick=()=>{settings.dashboardLogo='';settings.dashboardLogoName='';$('#dashLogoName').textContent='Logo dihapus. Simpan Tampilan untuk menerapkan.';$('#dashSettingsStatus').textContent='Logo dasbor dihapus dari konfigurasi, tidak menghapus file sumber.';};
 }
 $('#chooseDashLogo').onclick=async()=>{const a=await window.kaca.chooseDashboardAssets('logo');if(a?.length){settings.dashboardLogo=a[0].url;settings.dashboardLogoName=a[0].name;$('#dashLogoName').textContent=a[0].name;}};
 $('#chooseDashVideo').onclick=async()=>{const a=await window.kaca.chooseDashboardAssets('video');if(a?.length){settings.dashboardVideo=a[0].url;settings.dashboardVideoName=a[0].name;settings.dashboardImage='';settings.dashboardBackgroundDisabled=false;$('#dashVideoName').textContent=a[0].name;$('#dashImageName').textContent='Foto latar belum dipilih';}};
 $('#chooseDashImage').onclick=async()=>{const a=await window.kaca.chooseDashboardAssets('backgroundImage');if(a?.length){settings.dashboardImage=a[0].url;settings.dashboardImageName=a[0].name;settings.dashboardVideo='';settings.dashboardBackgroundDisabled=false;$('#dashImageName').textContent=a[0].name;$('#dashVideoName').textContent='Video tidak dipilih';}};
 $('#removeDashBackground').onclick=()=>{settings.dashboardVideo='';settings.dashboardImage='';settings.dashboardBackgroundDisabled=true;$('#dashVideoName').textContent='Dihapus';$('#dashImageName').textContent='Dihapus';$('#dashSettingsStatus').textContent='Latar foto dan video dinonaktifkan.';};
 $('#restoreDashBackground').onclick=()=>{settings.dashboardBackgroundDisabled=false;settings.dashboardVideo='';settings.dashboardImage='';$('#dashVideoName').textContent='Video animasi bawaan aktif';$('#dashImageName').textContent='Foto latar belum dipilih';$('#dashSettingsStatus').textContent='Latar bawaan akan digunakan.';};
 $('#addDashPhotos').onclick=async()=>{const a=await window.kaca.chooseDashboardAssets('photos');if(a?.length){settings.dashboardPhotos=[...(settings.dashboardPhotos||[]),...a].slice(0,30);await renderAppearance();$('#dashSettingsStatus').textContent='Foto ditambahkan. Simpan Tampilan untuk menerapkan perubahan.';}};
 document.querySelectorAll('[data-photo-remove]').forEach(b=>b.onclick=async()=>{settings.dashboardPhotos.splice(Number(b.dataset.photoRemove),1);await renderAppearance();});
 document.querySelectorAll('[data-photo-up],[data-photo-down]').forEach(b=>b.onclick=async()=>{const i=Number(b.dataset.photoUp??b.dataset.photoDown),j=b.hasAttribute('data-photo-up')?i-1:i+1;const a=settings.dashboardPhotos;[a[i],a[j]]=[a[j],a[i]];await renderAppearance();});
 $('#saveDashAppearance').onclick=async()=>{const pin=$('#dashPinInput').value.trim();if(!/^\d{4,8}$/.test(pin)){alert('PIN harus terdiri dari 4–8 angka.');return;}settings.dashboardTitle=$('#dashTitleInput').value.trim()||'KACA Studio';settings.adminPin=pin;settings.dashboardAccent=$('#dashAccentInput').value;settings.dashboardSurface=$('#dashSurfaceInput').value;settings.dashboardInk=$('#dashInkInput').value;settings.dashboardTheme=$('#dashThemeInput').value;applyAppTheme();await saveScopedSettings();$('#dashSettingsStatus').textContent='Pengaturan tampilan berhasil disimpan.';};
 const uiDefs={dashboard:[['brand','Logo & judul'],['preview','Layar preview'],['actions','Tombol Photo / Video'],['gallery','Galeri foto']],preview:[['header','Judul sesi'],['camera','Preview kamera'],['controls','Tombol pemotretan'],['gallery','Galeri foto sesi']],frame:[['header','Judul pemilihan frame'],['cards','Kartu frame'],['actions','Tombol lanjut']],filter:[['header','Judul filter'],['preview','Preview foto'],['cards','Kartu filter'],['actions','Tombol lanjut']],result:[['header','Judul hasil'],['photo','Foto hasil'],['actions','Tombol simpan / cetak']]};
 const uiDefault={dashboard:{brand:[12,8,76,8,'#d8b56a'],preview:[10,32,80,42,'#202024'],actions:[18,72,64,8,'#d23a2b'],gallery:[8,92,84,22,'#202024']},preview:{header:[8,5,84,12,'#d8b56a'],camera:[10,22,80,48,'#080809'],controls:[18,74,64,13,'#d23a2b'],gallery:[8,89,84,8,'#202024']},frame:{header:[8,5,84,12,'#d8b56a'],cards:[8,24,84,55,'#202024'],actions:[22,84,56,12,'#d23a2b']},filter:{header:[8,5,84,12,'#d8b56a'],preview:[8,22,100,60,'#080809'],cards:[60,24,100,55,'#202024'],actions:[22,84,56,12,'#d23a2b']},result:{header:[8,5,84,12,'#d8b56a'],photo:[20,20,100,58,'#080809'],actions:[8,82,84,13,'#d23a2b']}};
 let uiScreen='dashboard',uiSelected='preview';settings.uiDesigner=settings.uiDesigner||{};let uiDesignerDraft=JSON.parse(JSON.stringify(settings.uiDesignerApplied||{}));
 const uiLegacyDefaults={dashboard:{brand:[12,8,76,18,'#d8b56a'],preview:[10,32,80,34,'#202024'],actions:[18,72,64,18,'#d23a2b'],gallery:[8,92,84,7,'#202024']},preview:{header:[8,5,84,12,'#d8b56a'],camera:[10,22,80,48,'#080809'],controls:[18,74,64,13,'#d23a2b'],gallery:[8,89,84,8,'#202024']},frame:{header:[8,5,84,12,'#d8b56a'],cards:[8,24,84,55,'#202024'],actions:[22,84,56,12,'#d23a2b']},filter:{header:[8,5,84,12,'#d8b56a'],cards:[8,24,84,55,'#202024'],actions:[22,84,56,12,'#d23a2b']},result:{header:[8,5,84,12,'#d8b56a'],photo:[20,20,60,58,'#080809'],actions:[8,82,84,13,'#d23a2b']}};
 for(const [screen,parts] of Object.entries(uiLegacyDefaults)){for(const [key,d] of Object.entries(parts)){const saved=uiDesignerDraft?.[screen]?.[key];if(saved&&saved.x===d[0]&&saved.y===d[1]&&saved.w===d[2]&&saved.h===d[3]&&saved.color===d[4]&&(saved.opacity??100)===100&&(saved.scale??100)===100){uiDesignerDraft[screen][key]={x:uiDefault[screen][key][0],y:uiDefault[screen][key][1],w:uiDefault[screen][key][2],h:uiDefault[screen][key][3],color:uiDefault[screen][key][4],opacity:100,scale:100};}}}
 const uiComp=(screen,key)=>{uiDesignerDraft[screen]=uiDesignerDraft[screen]||{};return uiDesignerDraft[screen][key]||(uiDesignerDraft[screen][key]={x:uiDefault[screen][key][0],y:uiDefault[screen][key][1],w:uiDefault[screen][key][2],h:uiDefault[screen][key][3],color:uiDefault[screen][key][4],opacity:100,scale:100});};
 const uiScreens={
  dashboard:()=>dashboard(),
  preview:()=>`<div class="photo-session-content ui-preview-screen" data-flow-step="3"><div class="photo-flow-head" data-ui-part="header"><div><div class="eyebrow2">KACA.ID / CUSTOMER PHOTO SESSION</div><h2>Preview Kamera</h2><p>Pastikan posisi dan pencahayaan sudah sesuai, lalu mulai.</p></div><button class="btn secondary">Keluar dari Sesi</button></div><div class="photo-flow-steps"><div class="flow-step active"><b>01</b><span>Kamera</span></div><div class="flow-step"><b>02</b><span>Frame</span></div><div class="flow-step"><b>03</b><span>Foto</span></div><div class="flow-step"><b>04</b><span>Filter</span></div><div class="flow-step"><b>05</b><span>Hasil</span></div></div><div class="capture-grid" id="captureGrid" hidden><div class="panel"><div class="capture-preview" data-ui-part="camera"><div class="ui-real-camera-placeholder">LIVE CAMERA PREVIEW</div><button class="preview-start-button">MULAI SESI</button><div class="preview-bottom-controls" data-ui-part="controls"><button class="preview-tool-button">AMBIL FOTO</button></div></div><div class="capture-settings"><span>Countdown Capture · 3 detik</span></div></div><div class="panel"><div class="eyebrow2">SESSION PHOTOS</div><h3>Foto dalam Sesi</h3><div class="shot-counter">0 foto</div><div class="shot-gallery" data-ui-part="gallery"><div class="empty">Belum ada foto. Mulai sesi untuk mengambil gambar.</div></div></div></div></div>`,
  frame:()=>`<div class="photo-session-content ui-frame-screen" data-flow-step="2"><div class="photo-flow-head" data-ui-part="header"><div><div class="eyebrow2">KACA.ID / CUSTOMER PHOTO SESSION</div><h2>Pilih Frame</h2><p>Pilih desain dan jumlah foto pada frame.</p></div><button class="btn secondary">Keluar dari Sesi</button></div><div class="photo-flow-steps"><div class="flow-step done"><b>01</b><span>Kamera</span></div><div class="flow-step active"><b>02</b><span>Frame</span></div><div class="flow-step"><b>03</b><span>Foto</span></div><div class="flow-step"><b>04</b><span>Filter</span></div><div class="flow-step"><b>05</b><span>Hasil</span></div></div><section class="panel flow-frame-panel"><div class="eyebrow2">PILIH TEMPLATE</div><h3>Pilih Frame Foto</h3><p class="muted">Pilih frame yang akan digunakan untuk hasil cetak dan Live Photo.</p><div class="flow-frame-grid" data-ui-part="cards"></div><div class="notice">Frame memakai posisi, ukuran, dan pemetaan foto sumber yang tersimpan.</div></section><div class="flow-action-row" data-ui-part="actions"><button class="btn">LANJUT</button></div></div>`,
  filter:()=>`<div class="photo-session-content ui-filter-screen" data-flow-step="4"><div class="photo-flow-head"><div><div class="eyebrow2">KACA.ID / CUSTOMER PHOTO SESSION</div><h2>Pilih Filter</h2><p>Periksa foto dan tentukan tampilan hasil akhir.</p></div><button class="btn secondary">Keluar dari Sesi</button></div><div class="photo-flow-steps"><div class="flow-step done"><b>01</b><span>Kamera</span></div><div class="flow-step done"><b>02</b><span>Frame</span></div><div class="flow-step done"><b>03</b><span>Foto</span></div><div class="flow-step active"><b>04</b><span>Filter</span></div><div class="flow-step"><b>05</b><span>Hasil</span></div></div><section class="filter-review-panel"><div class="filter-review-head" data-ui-part="header"><div><div class="eyebrow2">KACA.ID / FILTER STUDIO</div><h3>Atur Nuansa Foto</h3><p>Pilih filter di kanan. Pratinjau di kiri menampilkan foto yang sudah tersusun di dalam frame.</p></div></div><div class="filter-review-layout"><div class="filter-preview-column"><div class="filter-preview-frame" data-ui-part="preview"><div class="ui-filter-photo">PREVIEW HASIL FOTO</div></div><div class="filter-preview-caption">PREVIEW HASIL CETAK · PROPORSI FRAME DIPERTAHANKAN</div></div><div class="filter-picker-column"><div class="filter-picker-title">PILIH FILTER</div><div class="filter-picker-grid" data-ui-part="cards"><button class="filter-option"><b>Sepia</b><small>Klasik cokelat antik</small></button><button class="filter-option"><b>Vintage</b><small>Nuansa nostalgia</small></button><button class="filter-option"><b>Mono</b><small>Hitam putih</small></button><button class="filter-option"><b>Cool</b><small>Biru cinematic</small></button></div><div class="filter-selected-note">Filter diterapkan ke foto hasil.</div><div id="filterNextMount" data-ui-part="actions"><button class="btn">LANJUT KE HASIL</button></div></div></div></section></div>`,
  result:()=>`<div class="photo-session-content ui-result-screen" data-flow-step="5"><div class="photo-flow-head"><div><div class="eyebrow2">KACA.ID / CUSTOMER PHOTO SESSION</div><h2>Hasil Sesi</h2><p>Semua hasil sesi siap dicetak dan dibagikan.</p></div><button class="btn secondary">SELESAI</button></div><div class="result-card"><div class="result-topline" data-ui-part="header"><b>Hasil sesi KACA-2026</b><span>Foto tersimpan · Live Photo diproses</span></div><div class="result-workspace"><section class="result-preview-column"><div class="result-preview-stage" data-ui-part="photo"><div class="ui-result-photo">HASIL FOTO DALAM FRAME</div></div><div class="result-preview-caption">HASIL FOTO DALAM FRAME</div></section><section class="result-files-column"><section class="drive-qr-card"><div class="drive-qr-copy"><b>SCAN QR CODE UNTUK HASIL DIGITAL</b><p>Scan untuk membuka folder Google Drive.</p></div><div class="ui-result-qr-placeholder">QR CODE</div></section><div class="result-share-controls" data-ui-part="actions"><div class="form-grid"><input placeholder="08xxxxxxxxxx"><input placeholder="nama@email.com"></div><div class="actions"><button class="btn">WhatsApp</button><button class="btn secondary">Email</button><button class="btn secondary">Cetak</button></div></div></section></div></div></div>`
 };
 const renderUiStage=()=>{
  const stage=$('#uiDesignerStage');stage.innerHTML=uiScreens[uiScreen]();
  stage.querySelectorAll('[data-ui-part]').forEach(el=>{
   const key=el.dataset.uiPart,c=uiComp(uiScreen,key),d=uiDefault[uiScreen][key];
   el.style.translate=`${(c.x-d[0])*0.5}vw ${(c.y-d[1])*0.5}vh`;el.style.setProperty('width',c.w+'%','important');el.style.setProperty('height',(c.h*0.5)+'vh','important');el.style.setProperty('min-height',(c.h*0.5)+'vh','important');el.style.opacity=String(c.opacity/100);el.style.setProperty('background-color',c.color,'important');el.style.setProperty('scale',String(c.scale/100),'important');el.classList.toggle('ui-design-selected',uiSelected===key);
   const handle=document.createElement('i');handle.className='ui-real-resize';handle.title='Tarik untuk mengubah ukuran';el.appendChild(handle);
   el.addEventListener('pointerdown',ev=>{
    if(ev.target.closest('button')&&!ev.target.classList.contains('ui-real-resize'))ev.preventDefault();
    ev.preventDefault();ev.stopPropagation();uiSelected=key;
    const resize=ev.target.classList.contains('ui-real-resize'),rect=stage.getBoundingClientRect(),sx=ev.clientX,sy=ev.clientY,ox=c.x,oy=c.y,ow=c.w,oh=c.h;
    el.setPointerCapture(ev.pointerId);
    const move=e=>{const dx=(e.clientX-sx)/rect.width*100,dy=(e.clientY-sy)/rect.height*100;if(resize){c.w=Math.max(10,Math.min(100,ow+dx));c.h=Math.max(6,Math.min(100,oh+dy));}else{c.x=Math.max(0,Math.min(100,ox+dx));c.y=Math.max(0,Math.min(100,oy+dy));}el.style.translate=`${(c.x-d[0])*0.5}vw ${(c.y-d[1])*0.5}vh`;el.style.setProperty('width',c.w+'%','important');el.style.setProperty('height',(c.h*0.5)+'vh','important');el.style.setProperty('min-height',(c.h*0.5)+'vh','important');};
    const up=()=>{el.removeEventListener('pointermove',move);el.removeEventListener('pointerup',up);renderUiStage();};el.addEventListener('pointermove',move);el.addEventListener('pointerup',up,{once:true});
   });
  });
  const c=uiComp(uiScreen,uiSelected);$('#uiDesignerSelectedTitle').textContent=uiDefs[uiScreen].find(x=>x[0]===uiSelected)?.[1]||'Pilih komponen';$('#uiDesignerColor').value=c.color;$('#uiDesignerOpacity').value=c.opacity;$('#uiDesignerScale').value=c.scale;
 };
 const applyUiDesigner=()=>{settings.uiDesigner=JSON.parse(JSON.stringify(uiDesignerDraft));settings.uiDesignerApplied=JSON.parse(JSON.stringify(uiDesignerDraft));applyUiDesignerTheme();};
 document.querySelectorAll('[data-ui-screen]').forEach(b=>b.onclick=()=>{uiScreen=b.dataset.uiScreen;uiSelected=uiDefs[uiScreen][0][0];document.querySelectorAll('[data-ui-screen]').forEach(x=>x.classList.toggle('active',x===b));renderUiStage();});
 $('#uiDesignerColor').oninput=e=>{uiComp(uiScreen,uiSelected).color=e.target.value;renderUiStage();};$('#uiDesignerOpacity').oninput=e=>{uiComp(uiScreen,uiSelected).opacity=Number(e.target.value);renderUiStage();};$('#uiDesignerScale').oninput=e=>{uiComp(uiScreen,uiSelected).scale=Number(e.target.value);renderUiStage();};
 $('#uiDesignerResetComponent').onclick=()=>{const d=uiDefault[uiScreen][uiSelected];uiDesignerDraft[uiScreen][uiSelected]={x:d[0],y:d[1],w:d[2],h:d[3],color:d[4],opacity:100,scale:100};renderUiStage();};
 $('#saveAdvancedTheme').onclick=async()=>{applyUiDesigner();await saveScopedSettings();$('#advancedThemeStatus').textContent='Tema visual berhasil disimpan.';};
 $('#resetAdvancedTheme').onclick=async()=>{uiDesignerDraft={};applyUiDesigner();await saveScopedSettings();renderUiStage();$('#advancedThemeStatus').textContent='Tema aktif dikembalikan ke default.';};
 renderUiStage();
}
async function initDashboardPreview(){
 const img=$('#dashLivePreview'),placeholder=$('#dashCameraPlaceholder'),state=$('#dashCameraState');
 try{
  let st=await api('/api/status');
  if(!st.camera_open){
   const savedId=String(settings.cameraDeviceId||'');
   if(savedId.startsWith('canon_edsdk_')) st=await api('/api/canon/open',{method:'POST',body:JSON.stringify({id:savedId})});
   else st=await api('/api/camera/open',{method:'POST',body:JSON.stringify({index:Number(settings.cameraDevice??1)})});
  }
  if(st.camera_open||st.ok){
   img.src='http://127.0.0.1:8765/api/stream.mjpg?dashboard='+Date.now();
   img.style.display='block';
   img.onload=()=>{placeholder.style.display='none';state.textContent='LIVE PREVIEW';};
   img.onerror=()=>{placeholder.style.display='grid';state.textContent='PREVIEW TERPUTUS';};
   state.textContent='KAMERA TERHUBUNG';
  }else{placeholder.style.display='grid';state.textContent='KAMERA BELUM TERBUKA';}
 }catch(e){placeholder.style.display='grid';state.textContent='KAMERA TIDAK TERSEDIA';}
}
function applyUiDesignerTheme(){
 const defaults={dashboard:{brand:[12,8],preview:[10,32],actions:[18,72],gallery:[8,92]},preview:{header:[8,5],camera:[10,22],controls:[18,74],gallery:[8,89]},frame:{header:[8,5],cards:[8,24],actions:[22,84]},filter:{header:[8,5],preview:[8,22],cards:[60,24],actions:[22,84]},result:{header:[8,5],photo:[20,20],actions:[8,82]}};
 const selectors={dashboard:{brand:'.studio-dashboard .dash-brand',preview:'.studio-dashboard .dash-camera-card',actions:'.studio-dashboard .dash-mode-actions',gallery:'.studio-dashboard .dash-gallery-section'},preview:{header:'.photo-session-content[data-flow-step="3"] .photo-flow-head',camera:'.photo-session-content[data-flow-step="3"] .capture-preview',controls:'.photo-session-content[data-flow-step="3"] .preview-bottom-controls',gallery:'.photo-session-content[data-flow-step="3"] .shot-gallery'},frame:{header:'.photo-session-content[data-flow-step="2"] .photo-flow-head',cards:'.photo-session-content[data-flow-step="2"] .flow-frame-grid',actions:'.photo-session-content[data-flow-step="2"] .flow-action-row'},filter:{header:'.photo-session-content[data-flow-step="4"] .filter-review-head',preview:'.photo-session-content[data-flow-step="4"] .filter-preview-frame',cards:'.photo-session-content[data-flow-step="4"] .filter-picker-grid,.photo-session-content[data-flow-step="4"] .filter-options',actions:'.photo-session-content[data-flow-step="4"] #filterNextMount'},result:{header:'.photo-session-content[data-flow-step="5"] .result-topline',photo:'.photo-session-content[data-flow-step="5"] .result-preview-stage',actions:'.photo-session-content[data-flow-step="5"] .result-share-controls'}};
 let style=document.getElementById('uiDesignerDynamicStyle');if(!style){style=document.createElement('style');style.id='uiDesignerDynamicStyle';document.head.appendChild(style);}let css='';for(const [screen,parts] of Object.entries(selectors)){for(const [key,selector] of Object.entries(parts)){const c=settings.uiDesignerApplied?.[screen]?.[key];if(!c)continue;const d=defaults[screen][key]||[0,0];css+=`${selector}{translate:${(c.x-d[0])}vw ${(c.y-d[1])}vh;scale:${Number(c.scale||100)/100}!important;width:${c.w}%;height:${c.h}vh!important;min-height:${c.h}vh!important;opacity:${Number(c.opacity??100)/100};background-color:${c.color}!important;}`;}}style.textContent=css;
}
function applyAppTheme(){
 const light=settings.dashboardTheme==='light';
 document.body.classList.toggle('kaca-light-theme',light);
 const root=document.documentElement.style;
 root.setProperty('--gold',settings.dashboardAccent||'#d8b56a');root.setProperty('--gold2',settings.dashboardAccent||'#f0d79c');
 root.setProperty('--kaca-ui-bg',settings.uiBg|| (light?'#f5f6f8':'#0b0b0d'));root.setProperty('--kaca-ui-panel',settings.uiPanel|| (light?'#ffffff':'#141416'));root.setProperty('--kaca-ui-text',settings.uiText|| (light?'#16181c':'#f4f1e9'));root.setProperty('--kaca-ui-muted',settings.uiMuted|| (light?'#60656e':'#88888f'));root.setProperty('--kaca-ui-border',settings.uiBorder|| (light?'#d8dce2':'#29292d'));
 root.setProperty('--kaca-preview-width',(Number(settings.uiPreviewWidth??100))+'%');root.setProperty('--kaca-preview-height',(Number(settings.uiPreviewHeight??260))+'px');root.setProperty('--kaca-preview-x',(Number(settings.uiPreviewX??0))+'px');root.setProperty('--kaca-preview-y',(Number(settings.uiPreviewY??0))+'px');root.setProperty('--kaca-logo-size',(Number(settings.uiLogoSize??84))+'px');root.setProperty('--kaca-logo-x',(Number(settings.uiLogoX??0))+'px');root.setProperty('--kaca-logo-y',(Number(settings.uiLogoY??0))+'px');root.setProperty('--kaca-button-scale',String(Number(settings.uiButtonScale??100)/100));root.setProperty('--kaca-button-x',(Number(settings.uiButtonX??0))+'px');root.setProperty('--kaca-button-y',(Number(settings.uiButtonY??0))+'px');root.setProperty('--kaca-result-width',(Number(settings.uiResultWidth??100))+'%');root.setProperty('--kaca-result-height',(Number(settings.uiResultHeight??420))+'px');root.setProperty('--kaca-frame-card-scale',String(Number(settings.uiFrameScale??100)/100));root.setProperty('--kaca-filter-card-scale',String(Number(settings.uiFilterScale??100)/100));root.setProperty('--kaca-preview-bg',settings.uiPreviewBg||'#050506');applyUiDesignerTheme();root.setProperty('--kaca-preview-alpha',(Number(settings.uiPreviewAlpha??100))+'%');root.setProperty('--kaca-result-alpha',(Number(settings.uiResultAlpha??100))+'%');
}
function openAdminPin(){
 document.querySelectorAll('.admin-pin-overlay').forEach(node=>node.remove());
 if(typeof closeKacaKeyboard==='function')closeKacaKeyboard();
 const overlay=document.createElement('div');overlay.className='admin-pin-overlay';
 overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');
 overlay.innerHTML=`<div class="admin-pin-card"><div class="admin-pin-icon">⌂</div><h2>Area Pengaturan</h2><p>Masukkan PIN Admin / Operator untuk melanjutkan.</p><form id="adminPinForm"><input id="adminPinEntry" type="password" inputmode="none" pattern="[0-9]*" maxlength="8" autocomplete="off" placeholder="Masukkan PIN" aria-label="PIN Admin"><div class="kaca-pin-keypad" aria-label="Keypad PIN">${['1','2','3','4','5','6','7','8','9','Hapus','0','⌫'].map(x=>`<button type="button" data-admin-digit="${x}">${x}</button>`).join('')}</div><small class="pin-error" id="adminPinError" aria-live="polite"></small><div class="actions"><button type="button" class="btn secondary" data-pin-cancel>Batal</button><button type="button" class="btn secondary" data-pin-recover>Perbaiki Input</button><button type="submit" class="btn" data-pin-submit>Masuk</button></div></form></div>`;
 document.body.appendChild(overlay);
 const input=overlay.querySelector('#adminPinEntry');let closed=false;
 const close=()=>{if(closed)return;closed=true;document.removeEventListener('keydown',esc,true);overlay.remove();};
 const esc=e=>{if(e.key==='Escape'){e.stopPropagation();close();}};
 document.addEventListener('keydown',esc,true);
 const focus=()=>{if(!closed&&overlay.isConnected){input.focus({preventScroll:true});input.setSelectionRange(input.value.length,input.value.length);}};
 const submit=()=>{if(input.value===String(settings.adminPin||'1234')){close();void go('appearance');}else{overlay.querySelector('#adminPinError').textContent='PIN tidak sesuai. Coba lagi.';input.value='';focus();}};
 overlay.querySelector('form').onsubmit=e=>{e.preventDefault();submit();};
 overlay.querySelectorAll('[data-admin-digit]').forEach(btn=>btn.onclick=()=>{const key=btn.dataset.adminDigit;if(key==='Hapus')input.value='';else if(key==='⌫')input.value=input.value.slice(0,-1);else input.value=(input.value+key).slice(0,8);input.dispatchEvent(new Event('input',{bubbles:true}));overlay.querySelector('#adminPinError').textContent='';focus();});
 overlay.querySelector('[data-pin-cancel]').onclick=close;
 overlay.querySelector('[data-pin-recover]').onclick=()=>{input.value='';overlay.querySelector('#adminPinError').textContent='Input telah dipulihkan. Masukkan PIN menggunakan keypad atau keyboard fisik.';focus();};
 overlay.addEventListener('click',e=>{if(e.target===overlay)close();});
 // inputMode="none" keeps the old virtual numeric pad from blocking this modal.
 setTimeout(focus,50);
}

const schemas={setup:[['Nama Booth','boothName','KACA.ID Studio'],['Tagline','tagline','Say Cheese, Say KACA'],['Folder Media','mediaRoot','KACA-ID-Media']],capture:[['Jumlah Foto per Sesi','photoCount','4'],['Countdown (detik)','countdown','3'],['Jeda Antarfoto (detik)','captureInterval','2'],['Retake Maksimum','retakeLimit','2']],frames:[['Ukuran Output','paperSize','4R','select'],['Orientasi','orientation','landscape','select'],['Slot Foto','frameSlots','4']],filters:[['Filter Pemotretan','defaultFilter','Natural','select'],['Kualitas JPEG','jpegQuality','94'],['DPI Cetak','printDpi','300','select']],output:[['Jumlah Salinan','printCopies','1'],['Simpan QR hasil','enableQR','true','select']],voucher:[['Prefix Voucher','voucherPrefix','KACA'],['Masa Berlaku (hari)','voucherExpiry','30'],['Batas Penggunaan','voucherUses','1']],payment:[['Pembayaran aktif','paymentEnabled','false','select'],['Harga Sesi (IDR)','sessionPrice','25000'],['Gateway','paymentGateway','manual','select'],['Mode','paymentEnvironment','sandbox','select']],appearance:[['Warna Aksen','accentColor','#D8B56A'],['Warna Tombol Preview','boothButtonColor','#D8B56A'],['Transparansi Tombol (%)','boothButtonOpacity','88'],['Ukuran Tombol (%)','boothButtonScale','100'],['Nama Logo','logoText','KACA.ID'],['Font UI','uiFont','Segoe UI']],license:[['Nama Pemilik Lisensi','licenseOwner',''],['Kode Aktivasi','activationCode',''],['ID Perangkat','deviceId','Otomatis saat aktivasi']]};
function selectOptions(key){if(key==='paperSize')return ['4R','2R Strip','Custom'];if(key==='printDpi')return ['300','600'];if(key==='orientation')return ['landscape','portrait'];if(key==='defaultFilter')return ['original','sepia','chrome','vintage','mono','cool','pencil','cartoon'];if(key==='paymentGateway')return ['manual','midtrans','doku','paypal','gopay'];if(key==='paymentEnvironment')return ['sandbox','production'];return ['false','true'];}
function renderKacaPager(container, count, current, onChange){
 const pages=Math.max(1,Math.ceil(count/10));
 if(pages<=1){container.replaceChildren();container.hidden=true;return;}
 container.hidden=false;
 const visible=[];
 for(let i=1;i<=pages;i++)if(i===1||i===pages||Math.abs(i-current)<=2)visible.push(i);
 const items=[];let previous=0;
 for(const number of visible){if(previous&&number>previous+1)items.push('<span class="kaca-page-ellipsis">…</span>');items.push(`<button type="button" class="btn secondary small ${number===current?'active':''}" data-kaca-page="${number}" ${number===current?'aria-current="page"':''}>${number}</button>`);previous=number;}
 container.innerHTML=`<button type="button" class="btn secondary small" data-kaca-page="${current-1}" ${current<=1?'disabled':''}>Kembali</button>${items.join('')}<button type="button" class="btn secondary small" data-kaca-page="${current+1}" ${current>=pages?'disabled':''}>Lanjut</button><span class="kaca-page-info">${count} item · halaman ${current}/${pages}</span>`;
 container.querySelectorAll('[data-kaca-page]').forEach(button=>button.onclick=()=>{
   const next=Number(button.dataset.kacaPage);
   if(next!==current&&next>=1&&next<=pages)onChange(next);
 });
}

async function renderVoucherAdmin(){
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / VOUCHER MANAGER</div><h3>Generator Voucher</h3><p class="muted">Buat voucher otomatis 5 karakter (gabungan huruf besar dan angka), atau tentukan kode custom sendiri.</p><div class="form-grid"><div class="field"><label>Jumlah voucher</label><input id="voucherBatchCount" type="number" min="1" max="1000" value="10"></div><div class="field"><label>Masa berlaku (hari)</label><input id="voucherExpiryDays" type="number" min="1" max="3650" value="30"></div><div class="field"><label>Batas penggunaan per kode</label><input id="voucherMaxUses" type="number" min="1" max="100000" value="1"></div><div class="field"><label>Kode custom (opsional)</label><input id="voucherCustomCode" maxlength="32" placeholder="Contoh: PROMOKACA2026"><small class="field-help">Huruf besar dan angka, 3–32 karakter. Jika diisi, jumlah harus 1.</small></div></div><div class="actions wrap"><button class="btn" id="generateVouchers">GENERATE VOUCHER</button><button class="btn secondary" id="refreshVouchers">Muat Ulang</button><button class="btn secondary" id="downloadVoucherCsvTemplate">Unduh Template CSV</button></div><div class="field"><label>Import voucher dari CSV (Excel)</label><input id="voucherCsvFile" type="file" accept=".csv,text/csv"><small class="field-help">Kolom wajib: code. Kolom opsional: expires_at, max_uses, used_count, active atau expiry_days. Simpan file Excel sebagai CSV UTF-8.</small></div><div class="actions"><button class="btn secondary" id="importVoucherCsv">IMPORT VOUCHER CSV</button></div><div id="voucherAdminStatus" class="notice">Kode otomatis selalu unik dan disimpan secara lokal.</div></div><div class="panel"><div class="eyebrow2">DAFTAR KODE</div><h3>Voucher Tersimpan</h3><div class="actions wrap voucher-bulk-actions"><label class="frame-enable-check"><input type="checkbox" id="voucherSelectAll"><span>Pilih semua voucher</span></label><button class="btn secondary" id="deleteSelectedVouchers">Hapus terpilih</button><button class="btn secondary" id="deleteExpiredVouchers">Hapus yang kedaluwarsa</button><button class="btn danger" id="deleteAllVouchers">Hapus seluruh voucher</button></div><div id="voucherSelectionCount" class="field-help">0 voucher dipilih.</div><div id="voucherTable"><div class="empty">Memuat voucher…</div></div></div>`;
 const status=$('#voucherAdminStatus'), table=$('#voucherTable');
 let voucherPage=1;const voucherPager=document.createElement('nav');voucherPager.className='kaca-pager';voucherPager.setAttribute('aria-label','Halaman voucher');table.insertAdjacentElement('afterend',voucherPager);
 const selectedVoucherCodes=()=>Array.from(table.querySelectorAll('[data-voucher-select]:checked')).map(x=>x.value);
 const updateVoucherSelection=()=>{const count=selectedVoucherCodes().length,total=table.querySelectorAll('[data-voucher-select]').length,master=$('#voucherSelectAll'),label=$('#voucherSelectionCount');if(master){master.checked=total>0&&count===total;master.indeterminate=count>0&&count<total;}if(label)label.textContent=`${count} dari ${total} voucher dipilih.`;};
 const bulkDelete=async(payload,confirmText)=>{if(!(await kacaConfirm(confirmText)))return;const buttons=['#deleteSelectedVouchers','#deleteExpiredVouchers','#deleteAllVouchers'].map(x=>$(x)).filter(Boolean);buttons.forEach(b=>b.disabled=true);try{const r=await api('/api/vouchers/delete',{method:'POST',body:JSON.stringify(payload)});status.textContent=`Berhasil menghapus ${Number(r.deleted||0)} voucher.`;await load();}catch(e){status.textContent='Gagal menghapus voucher: '+e.message;}finally{buttons.forEach(b=>b.disabled=false);}};
 $('#deleteSelectedVouchers').onclick=()=>{const codes=selectedVoucherCodes();if(!codes.length){status.textContent='Pilih minimal satu voucher terlebih dahulu.';return;}bulkDelete({codes},`Hapus ${codes.length} voucher yang dipilih? Tindakan ini tidak dapat dibatalkan.`);};
 $('#deleteExpiredVouchers').onclick=()=>bulkDelete({mode:'expired'},'Hapus semua voucher yang sudah melewati tanggal kedaluwarsa? Tindakan ini tidak dapat dibatalkan.');
 $('#deleteAllVouchers').onclick=()=>bulkDelete({mode:'all'},'PERINGATAN: Hapus seluruh voucher yang tersimpan, termasuk voucher yang masih aktif? Tindakan ini tidak dapat dibatalkan.');
 const load=async()=>{try{const r=await api('/api/vouchers');const rows=r.vouchers||[];voucherPage=Math.min(voucherPage,Math.max(1,Math.ceil(rows.length/10)));renderKacaPager(voucherPager,rows.length,voucherPage,next=>{voucherPage=next;void load();});table.innerHTML=rows.length?`<div class="table-scroll"><table class="data-table"><thead><tr><th>Pilih</th><th>Kode</th><th>Status</th><th>Penggunaan</th><th>Kadaluarsa</th><th>Aksi</th></tr></thead><tbody>${rows.slice((voucherPage-1)*10,voucherPage*10).map(v=>`<tr><td><input type="checkbox" data-voucher-select value="${esc(v.code)}" aria-label="Pilih voucher ${esc(v.code)}"></td><td><b class="voucher-code-cell">${esc(v.code)}</b>${v.custom?' · custom':''}</td><td>${esc(v.status)}</td><td>${Number(v.used_count||0)} / ${Number(v.max_uses||1)}</td><td>${esc(v.expires_at||'-')}</td><td><button class="btn small ${v.active?'secondary':''}" data-voucher-toggle="${esc(v.code)}" data-active="${v.active?'1':'0'}">${v.active?'Nonaktifkan':'Aktifkan'}</button></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">Belum ada voucher. Generate kode pertama di atas.</div>';
 const selectAll=$('#voucherSelectAll');if(selectAll){selectAll.checked=false;selectAll.indeterminate=false;selectAll.onchange=()=>{table.querySelectorAll('[data-voucher-select]').forEach(c=>c.checked=selectAll.checked);updateVoucherSelection();};}table.querySelectorAll('[data-voucher-select]').forEach(c=>c.onchange=updateVoucherSelection);updateVoucherSelection();
 table.querySelectorAll('[data-voucher-toggle]').forEach(btn=>btn.onclick=async()=>{btn.disabled=true;try{await api('/api/vouchers/toggle',{method:'POST',body:JSON.stringify({code:btn.dataset.voucherToggle,active:btn.dataset.active!=='1'})});await load();}catch(e){status.textContent='Gagal mengubah voucher: '+e.message;btn.disabled=false;}});
 }catch(e){table.innerHTML=`<div class="notice">Gagal memuat voucher: ${esc(e.message)}</div>`;}};
 $('#generateVouchers').onclick=async()=>{const btn=$('#generateVouchers');try{btn.disabled=true;btn.textContent='Membuat…';const r=await api('/api/vouchers/generate',{method:'POST',body:JSON.stringify({count:Number($('#voucherBatchCount').value)||1,expiry_days:Number($('#voucherExpiryDays').value)||30,max_uses:Number($('#voucherMaxUses').value)||1,custom_code:$('#voucherCustomCode').value.trim()})});status.textContent=`Berhasil membuat ${r.count} voucher: ${(r.created||[]).map(v=>v.code).join(', ')}`;$('#voucherCustomCode').value='';await load();}catch(e){status.textContent='Gagal membuat voucher: '+e.message;}finally{btn.disabled=false;btn.textContent='GENERATE VOUCHER';}};
 $('#refreshVouchers').onclick=load;
 $('#downloadVoucherCsvTemplate').onclick=()=>{const csv='code,expires_at,max_uses,used_count,active\nKACA1,2026-12-31,1,0,true\nPROMO2026,2026-12-31T23:59:59,5,0,true\n';const blob=new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='template-voucher-kaca-id.csv';a.click();URL.revokeObjectURL(url);};
 const parseCsv=text=>{const rows=[];const firstLine=(text.split(/\r?\n/).find(v=>v.trim())||'');const delimiter=(firstLine.split(';').length>firstLine.split(',').length)?';':',';let row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){const ch=text[i];if(ch==='"'&&quoted&&text[i+1]==='"'){cell+='"';i++;}else if(ch==='"'){quoted=!quoted;}else if(ch===delimiter&&!quoted){row.push(cell);cell='';}else if((ch==='\n'||ch==='\r')&&!quoted){if(ch==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v.trim()))rows.push(row);row=[];cell='';}else cell+=ch;}row.push(cell);if(row.some(v=>v.trim()))rows.push(row);if(rows.length<2)throw new Error('CSV harus memiliki header dan minimal satu baris voucher.');const headers=rows.shift().map(h=>h.replace(/^\ufeff/,'').trim().toLowerCase().replace(/[ \-/]+/g,'_'));return rows.map(cols=>Object.fromEntries(headers.map((h,i)=>[h,(cols[i]||'').trim()]))).filter(x=>x.code||x.kode);};
 $('#importVoucherCsv').onclick=async()=>{const btn=$('#importVoucherCsv'),file=$('#voucherCsvFile').files[0];if(!file){status.textContent='Pilih file CSV terlebih dahulu.';return;}try{btn.disabled=true;btn.textContent='Mengimpor…';const csv=await file.text();const vouchers=parseCsv(csv);const result=await api('/api/vouchers/import',{method:'POST',body:JSON.stringify({vouchers})});status.textContent=`Import selesai: ${result.imported} voucher berhasil, ${result.skipped?.length||0} baris dilewati.`+(result.skipped?.length?' Detail: '+result.skipped.slice(0,8).map(x=>`baris ${x.row} ${x.code||''}: ${x.reason}`).join(' | '):'');await load();}catch(e){status.textContent='Gagal import CSV: '+e.message;}finally{btn.disabled=false;btn.textContent='IMPORT VOUCHER CSV';}};
 await load();
}
async function renderPaymentSettings(){
 const pageGeneration=navigationGeneration;
 const current=await api('/api/qris/status').catch(()=>({configured:false}));
 if(pageGeneration!==navigationGeneration)return;
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / PAYMENT METHODS</div><h3>Metode Transaksi Pelanggan</h3><p class="muted">Aktifkan metode yang ingin ditampilkan pada layar transaksi pelanggan. Jika keduanya dinonaktifkan, layar transaksi dilewati dan pelanggan langsung memilih frame.</p><div class="form-grid"><label class="frame-enable-check"><input type="checkbox" id="enableVoucherPayment" ${settings.enableVoucherPayment!==false?'checked':''}><span>Aktifkan pembayaran Voucher</span></label><label class="frame-enable-check"><input type="checkbox" id="enableQrisPayment" ${settings.enableQrisPayment!==false?'checked':''}><span>Aktifkan pembayaran QRIS</span></label></div><div class="actions"><button class="btn" id="savePaymentMethods">Simpan Metode Transaksi</button></div><div class="notice" id="paymentMethodsStatus">Metode aktif: ${settings.enableVoucherPayment!==false?'Voucher ':''}${settings.enableQrisPayment!==false?'QRIS':''}.</div></div><div class="panel"><div class="eyebrow2">KACA.ID / PAYMENT CONFIGURATION</div><h3>Konfigurasi QRIS</h3><p class="muted">Unggah gambar QRIS merchant dari bank atau penyedia pembayaran. Mode ini menggunakan QRIS statis dengan verifikasi manual oleh operator.</p><div class="form-grid"><div class="field"><label>Nama merchant</label><input id="qrisMerchantName" maxlength="100" value="${esc(current.merchant_name||'')}"></div><div class="field"><label>Nominal sesi (IDR)</label><input id="qrisAmount" type="number" min="0" value="${Number(current.amount||settings.sessionPrice||25000)}"></div><div class="field" style="grid-column:1/-1"><label>Petunjuk pembayaran</label><textarea id="qrisInstructions" rows="3">${esc(current.instructions||'Scan QRIS, lalu tunjukkan bukti pembayaran kepada operator.')}</textarea></div><div class="field" style="grid-column:1/-1"><label>Gambar QRIS (PNG/JPEG, maks. 5 MB)</label><input id="qrisImageFile" type="file" accept="image/png,image/jpeg"><small class="field-help">${current.configured?'QRIS sudah terpasang. Pilih file baru hanya jika ingin menggantinya.':'Belum ada gambar QRIS yang dipasang.'}</small></div></div><div id="qrisCurrentPreview" style="margin:16px 0">${current.configured?'<img src="http://127.0.0.1:8765/api/qris/image?v='+Date.now()+'" alt="QRIS merchant" style="display:block;max-width:280px;max-height:280px;object-fit:contain;background:white;padding:12px;border-radius:12px">':'<div class="empty">Preview QRIS akan tampil setelah disimpan.</div>'}</div><div class="actions"><button class="btn" id="saveQrisConfig">Simpan Konfigurasi QRIS</button></div><div class="notice" id="qrisConfigStatus">${current.configured?'QRIS statis siap ditampilkan. Pembayaran tetap harus diverifikasi operator.':'Unggah QRIS merchant agar pilihan QRIS tersedia bagi pelanggan.'}</div></div><div class="panel"><h3>Catatan Integrasi</h3><p class="muted">QRIS dinamis dan konfirmasi pembayaran otomatis memerlukan akun serta Server Key dari payment gateway (misalnya Midtrans atau DOKU). Source ini tidak akan menganggap pembayaran berhasil hanya karena pelanggan menekan tombol konfirmasi.</p></div>`;
 $('#saveQrisConfig').onclick=async()=>{const btn=$('#saveQrisConfig'),status=$('#qrisConfigStatus');try{btn.disabled=true;btn.textContent='Menyimpan…';let image_data_url='';const file=$('#qrisImageFile').files[0];if(file){if(file.size>5*1024*1024)throw new Error('Ukuran gambar maksimal 5 MB.');image_data_url=await new Promise((resolve,reject)=>{const rd=new FileReader();rd.onload=()=>resolve(rd.result);rd.onerror=()=>reject(new Error('Gagal membaca file QRIS.'));rd.readAsDataURL(file);});}const r=await api('/api/qris/config',{method:'POST',body:JSON.stringify({merchant_name:$('#qrisMerchantName').value.trim(),amount:Number($('#qrisAmount').value)||0,instructions:$('#qrisInstructions').value.trim(),image_data_url})});status.textContent=r.ok?'Konfigurasi QRIS tersimpan. QRIS statis aktif; operator harus memeriksa transaksi sebelum mengizinkan sesi.':'Konfigurasi belum tersimpan.';$('#qrisCurrentPreview').innerHTML='<img src="http://127.0.0.1:8765/api/qris/image?v='+Date.now()+'" alt="QRIS merchant" style="display:block;max-width:280px;max-height:280px;object-fit:contain;background:white;padding:12px;border-radius:12px">';}catch(e){status.textContent='Gagal menyimpan QRIS: '+e.message;}finally{btn.disabled=false;btn.textContent='Simpan Konfigurasi QRIS';}}; $('#savePaymentMethods').onclick=async()=>{settings.enableVoucherPayment=$('#enableVoucherPayment').checked;settings.enableQrisPayment=$('#enableQrisPayment').checked;await saveScopedSettings();$('#paymentMethodsStatus').textContent='Metode transaksi tersimpan. '+(!settings.enableVoucherPayment&&!settings.enableQrisPayment?'Layar transaksi akan dilewati.':'');};
 // v0.9.76: DOKU Checkout QRIS (real provider verification, sandbox/production).
 $('#content').insertAdjacentHTML('beforeend',`<div class="panel"><div class="eyebrow2">KACA.ID / QRIS DINAMIS</div><h3>QRIS Otomatis — DOKU Checkout</h3><p class="muted">Gunakan Client ID dan Secret Key dari DOKU. QRIS Checkout dipilih khusus untuk satu invoice; verifikasi otomatis hanya berhasil bila DOKU mengembalikan status SUCCESS. QRIS statis tetap tersedia sebagai alternatif dengan PIN operator.</p><div class="form-grid"><div class="field"><label>Mode pembayaran QRIS</label><select id="qrisIntegrationMode"><option value="static_manual">QRIS Statis · verifikasi PIN operator</option><option value="doku_checkout">DOKU Checkout QRIS · verifikasi otomatis</option></select></div><div class="field"><label>Lingkungan DOKU</label><select id="dokuEnvironment"><option value="sandbox">Sandbox (pengujian)</option><option value="production">Production (pembayaran nyata)</option></select></div><div class="field"><label>Client ID DOKU</label><input id="dokuClientId" autocomplete="off" placeholder="Client ID merchant"></div><div class="field"><label>Secret Key DOKU</label><input id="dokuSecretKey" type="password" autocomplete="new-password" placeholder="Masukkan Secret Key"></div></div><div class="actions"><button type="button" class="btn" id="saveDokuGateway">Simpan QRIS Otomatis</button></div><div id="dokuGatewayStatus" class="notice">Memeriksa integrasi DOKU…</div><small class="field-help">Pada mode DOKU, simpan nominal di Konfigurasi QRIS pada panel di atas. Checkout DOKU menampilkan QRIS dan status dipastikan melalui permintaan server-to-server. Tidak ada konfirmasi berhasil palsu.</small></div>`);
 $('#qrisIntegrationMode').value=current.mode==='doku_checkout'?'doku_checkout':'static_manual';
 $('#dokuEnvironment').value=current.doku?.environment||'sandbox';
 $('#dokuClientId').value=current.doku?.client_id||'';
 $('#dokuSecretKey').placeholder=current.doku?.secret_saved?'Secret sudah tersimpan (kosongkan untuk memakai yang lama)':'Masukkan Secret Key';
 $('#dokuGatewayStatus').textContent=current.doku?.configured?'DOKU tersimpan: '+(current.doku.environment||'sandbox')+'. Pilih mode DOKU untuk mengaktifkan.':'DOKU belum dikonfigurasi.';
 $('#saveDokuGateway').onclick=async()=>{const button=$('#saveDokuGateway');try{button.disabled=true;const r=await api('/api/qris/gateway/config',{method:'POST',body:JSON.stringify({mode:$('#qrisIntegrationMode').value,client_id:$('#dokuClientId').value.trim(),secret_key:$('#dokuSecretKey').value.trim(),environment:$('#dokuEnvironment').value})});$('#dokuSecretKey').value='';$('#dokuGatewayStatus').textContent=r.mode==='doku_checkout'?'QRIS DOKU aktif. Pembayaran hanya dianggap berhasil berdasarkan status transaksi DOKU.':'QRIS statis aktif; perlu verifikasi operator.';}catch(e){$('#dokuGatewayStatus').textContent='Gagal menyimpan: '+e.message;}finally{button.disabled=false;}};

}
function renderForm(page){let fields=schemas[page]||[];return `<div class="panel"><div class="eyebrow2">KACA.ID / ${page.toUpperCase()}</div><h3>${titles[page]}</h3><p class="muted">${descriptions[page]}</p><div class="form-grid">${fields.map(([label,key,def,type])=>{let value=settings[key]??def;return `<div class="field"><label>${label}</label>${type==='select'?`<select data-key="${key}">${selectOptions(key).map(v=>`<option value="${v}" ${String(value)===v?'selected':''}>${v}</option>`).join('')}</select>`:`<input data-key="${key}" value="${String(value).replaceAll('"','&quot;')}" ${(['accentColor','boothButtonColor'].includes(key)?'type="color"':(['boothButtonOpacity','boothButtonScale'].includes(key)?'type="number" min="10" max="140" step="1"':''))}>`}</div>`}).join('')}</div><div class="actions"><button class="btn" id="save">Simpan Pengaturan</button><button class="btn secondary" id="reset">Reset Form</button></div></div>`}
function requestVoucherCode(){return new Promise(resolve=>{const overlay=document.createElement('div');overlay.className='session-pin-overlay';overlay.innerHTML=`<form class="session-pin-card voucher-entry-card"><div class="eyebrow2">KACA.ID / VOUCHER</div><h3>Masukkan Kode Voucher</h3><p>Masukkan kode voucher yang diberikan oleh admin.</p><input id="voucherCustomerCode" type="text" maxlength="32" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="CONTOH A7K2P" required><div class="voucher-virtual-keyboard" aria-label="Keyboard voucher"><div class="voucher-key-row">${'1234567890'.split('').map(k=>`<button type="button" data-voucher-key="${k}">${k}</button>`).join('')}</div>${['QWERTYUIOP','ASDFGHJKL','ZXCVBNM'].map(row=>`<div class="voucher-key-row">${row.split('').map(k=>`<button type="button" data-voucher-key="${k}">${k}</button>`).join('')}</div>`).join('')}<div class="voucher-key-row voucher-key-actions"><button type="button" data-voucher-action="backspace">⌫ HAPUS</button><button type="button" data-voucher-action="clear">BERSIHKAN</button></div></div><small class="pin-error" id="voucherEntryError" aria-live="polite"></small><div class="actions"><button type="button" class="btn secondary" data-voucher-cancel>Batal</button><button type="submit" class="btn">Periksa Voucher</button></div></form>`;document.body.appendChild(overlay);const form=overlay.querySelector('form'),input=overlay.querySelector('#voucherCustomerCode');const close=value=>{overlay.remove();resolve(value);};overlay.querySelector('[data-voucher-cancel]').onclick=()=>close(null);overlay.addEventListener('click',e=>{if(e.target===overlay)close(null);});overlay.querySelectorAll('[data-voucher-key]').forEach(key=>key.onclick=()=>{input.value=(input.value+key.dataset.voucherKey).slice(0,32);input.focus();});overlay.querySelector('[data-voucher-action="backspace"]').onclick=()=>{input.value=input.value.slice(0,-1);input.focus();};overlay.querySelector('[data-voucher-action="clear"]').onclick=()=>{input.value='';input.focus();};form.onsubmit=e=>{e.preventDefault();const code=input.value.trim().toUpperCase();if(!/^[A-Z0-9]{3,32}$/.test(code)){overlay.querySelector('#voucherEntryError').textContent='Kode harus 3–32 karakter huruf dan angka.';input.focus();return;}close(code);};input.focus();});}
async function api(path,options={}){const headers={Accept:'application/json',...(options.headers||{})};if(options.body!==undefined&&options.body!==null&&!Object.keys(headers).some(k=>k.toLowerCase()==='content-type'))headers['Content-Type']='text/plain;charset=UTF-8';const controller=typeof AbortController!=='undefined'?new AbortController():null;const timer=controller?setTimeout(()=>controller.abort(),20000):null;try{const r=await fetch(`http://127.0.0.1:8765${path}`,{...options,headers,signal:controller?controller.signal:options.signal});let d;try{d=await r.json()}catch{throw new Error(`Backend membalas HTTP ${r.status}`)}if(!r.ok)throw new Error(d.error||`HTTP ${r.status}`);return d;}catch(e){if(e.name==='AbortError')throw new Error('Backend tidak merespons dalam 20 detik. Periksa status backend kamera.');if(e instanceof TypeError)throw new Error('Tidak dapat terhubung ke backend lokal (127.0.0.1:8765). Backend mungkin berhenti atau koneksi lokal diblokir.');throw e;}finally{if(timer)clearTimeout(timer);}}
// KACA.ID v0.9.83 — group existing settings without recreating controls or losing handlers.
function mountGeneralSettingsSubmenus(onCameraOpen){
 const content=$('#content');if(!content)return;
 const labels={storage:'Umum',sharing:'Share File',camera:'Kamera & Video',logs:'App Logs'};
 const sections={
  'Lokasi Penyimpanan Lokal':'storage',
  'Penyimpanan & Berbagi Otomatis Google Drive':'storage',
  'Metode Pengiriman WhatsApp':'sharing',
  'Konfigurasi WhatsApp Cloud API':'sharing',
  'Mode yang Ditampilkan di Dasbor':'sharing',
  'Gateway Fonnte — Tanpa WhatsApp Cloud API langsung':'sharing',
  'Diagnostik Koneksi Fonnte':'sharing',
  'Pengaturan Kamera':'camera',
  'Kualitas Foto, Video & Cetakan':'camera',
  'Orientasi & Flip Kamera':'camera',
  'Pengaturan Kualitas Live Preview':'camera',
  'Kontrol Profesional Kamera':'camera',
  'App Logs · Catatan Permasalahan':'logs'
 };
 const panels=Array.from(content.children).filter(n=>n.classList?.contains('panel'));
 for(const panel of panels){
   const children=Array.from(panel.children);
   const headings=children.filter(n=>n.matches?.('h3'));
   // Headings are structural boundaries, not pieces of a single long scroll.
   if(headings.length<2){
     const title=(panel.querySelector('h3')?.textContent||'').trim();
     panel.dataset.settingsGroup=sections[title]||'storage';continue;
   }
   let part=null;
   for(const child of children){
     if(child.matches?.('h3')||!part){
       const title=child.matches?.('h3')?child.textContent.trim():(headings[0]?.textContent.trim()||'');
       if(!part||child.matches?.('h3')){
         part=document.createElement('section');part.className='kaca-general-subsection';
         part.dataset.settingsGroup=sections[title]||'camera';panel.appendChild(part);
       }
     }
     part.appendChild(child);
   }
 }
 const nav=document.createElement('nav');nav.className='kaca-general-tabs';nav.setAttribute('aria-label','Submenu Pengaturan Umum');
 nav.innerHTML=Object.entries(labels).map(([key,title])=>`<button type="button" data-settings-tab="${key}" class="btn secondary" aria-pressed="false">${title}</button>`).join('');
 content.prepend(nav);
 const tab=async(key)=>{
   nav.querySelectorAll('[data-settings-tab]').forEach(button=>{const active=button.dataset.settingsTab===key;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
   for(const panel of panels){
     const groups=panel.querySelectorAll(':scope > .kaca-general-subsection');
     if(groups.length){let visible=0;groups.forEach(group=>{group.hidden=group.dataset.settingsGroup!==key;if(!group.hidden)visible++;});panel.hidden=visible===0;}
     else panel.hidden=panel.dataset.settingsGroup!==key;
   }
   if(key==='camera')try{await onCameraOpen?.();}catch(e){console.warn('[CAMERA_AUTO_PREVIEW]',e);}
   else if(typeof window.kacaCameraPreviewStop==='function')window.kacaCameraPreviewStop();
 };
 nav.querySelectorAll('button').forEach(button=>button.onclick=()=>tab(button.dataset.settingsTab));
 // Keep last selected submenu within the running application session.
 const previous=window.kacaGeneralSettingsTab||'storage';
 const selected=labels[previous]?previous:'storage';
 window.kacaGeneralSettingsTab=selected;
 const originalTab=tab;
 nav.querySelectorAll('button').forEach(button=>button.onclick=async()=>{
   const selectedKey=button.dataset.settingsTab;
   window.kacaGeneralSettingsTab=selectedKey;
   const request=kacaMenuRequest;
   await originalTab(selectedKey);
   await kacaCheckAfterPaint();
   if(request!==kacaMenuRequest||window.kacaCurrentMenu!=='generalSettings')return;
   const health=kacaMenuHealth('generalSettings');
   if(!health.ok){
     console.warn('[KACA_SUBMENU_INCOMPLETE]',selectedKey,health.reason);
     if(kacaMenuUserEdited)kacaShowMenuRecovery('generalSettings',health.reason);
     else void go('generalSettings',{autoRecovered:true});
   }
 });
 void tab(selected);
}

async function renderGeneralSettings(){
 const pageGeneration=navigationGeneration;
 const [driveState,cameras]=await Promise.all([
  api('/api/google-drive/status').catch(()=>({configured:false,connected:false,jobs:[]})),
  api('/api/cameras').catch(()=>({cameras:[],scan_done:false}))
 ]);
 if(pageGeneration!==navigationGeneration)return;
 // Do not block the settings screen while Windows enumerates cameras. The explicit
 // camera detection controls below can refresh the list after the screen is visible.
 const opts=(cameras.cameras||[]).map(c=>`<option value="${c.id}">${c.label}</option>`).join('');
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / LOCAL STORAGE</div><h3>Lokasi Penyimpanan Lokal</h3><p class="muted">Tentukan folder utama untuk menyimpan semua hasil sesi. Folder Photos, Live_Photos, Final_Results, dan ZIP akan dibuat otomatis.</p><div class="form-grid"><div class="field" style="grid-column:1/-1"><label>Folder penyimpanan</label><input id="localStoragePath" readonly value="${esc(settings.localStoragePath||'Pictures\\KACA STUDIO (default)')}"><small class="field-help">Lokasi baru langsung dipakai untuk sesi berikutnya. Data sesi lama tidak dipindahkan otomatis.</small></div></div><div class="actions"><button class="btn secondary" id="chooseLocalStorage">Pilih Folder</button><button class="btn" id="saveLocalStorage">Simpan Lokasi</button></div><div class="notice" id="localStorageStatus">Penyimpanan saat ini: ${esc(settings.localStoragePath||'Pictures\\KACA STUDIO')}.</div></div><div class="panel"><div class="eyebrow2">KACA.ID / GOOGLE DRIVE CLOUD</div><h3>Penyimpanan & Berbagi Otomatis Google Drive</h3><p class="muted">Hasil sesi disimpan ke folder lokal terlebih dahulu. Setelah itu KACA.ID mengunggahnya di latar belakang, membuat tautan folder sesi, dan mengantrekan ulang unggahan ketika koneksi terputus.</p><div class="notice" id="googleDriveStatus">${driveState.connected?'Google Drive sudah terhubung.':'Google Drive belum terhubung.'}</div><div class="form-grid"><div class="field"><label>Google OAuth Client ID</label><input id="googleDriveClientId" autocomplete="off" value="${esc(driveState.client_id||'')}" placeholder="xxxxx.apps.googleusercontent.com"></div><div class="field"><label>Google OAuth Client Secret</label><input id="googleDriveClientSecret" type="password" autocomplete="new-password" placeholder="Kosongkan jika sudah tersimpan"></div></div><small class="field-help">Buat OAuth Client ID bertipe Desktop App di Google Cloud Console dan aktifkan Google Drive API. KACA.ID menggunakan izin drive.file. Client Secret disimpan lokal di komputer booth.</small><div class="actions wrap"><button class="btn" id="connectGoogleDrive">Simpan & Hubungkan Google Drive</button><button class="btn secondary" id="retryGoogleDrive">Coba Ulang Antrean Upload</button><button class="btn secondary" id="disconnectGoogleDrive">Putuskan Akun</button></div><div class="notice" id="googleDriveJobs">${(driveState.jobs||[]).filter(j=>j.status!=='ready').length} unggahan menunggu atau sedang diproses.</div></div><div class="panel"><div class="eyebrow2">KACA.ID / WHATSAPP</div><h3>Metode Pengiriman WhatsApp</h3><p class="muted">Pilih metode yang digunakan pada layar hasil sesi. Pengaturan ini dapat diubah kapan saja.</p><div class="field"><label>Metode pengiriman aktif</label><select id="waDeliveryMode"><option value="click_to_chat" ${settings.waDeliveryMode==='click_to_chat'?'selected':''}>Click-to-Chat · operator menekan Kirim di WhatsApp</option><option value="gateway_fonnte" ${settings.waDeliveryMode==='gateway_fonnte'?'selected':''}>Gateway Fonnte · kirim tanpa membuka WhatsApp</option><option value="cloud_api" ${!['click_to_chat','gateway_fonnte'].includes(settings.waDeliveryMode)?'selected':''}>WhatsApp Cloud API · kirim otomatis dari KACA.ID</option></select><small class="field-help">Click-to-Chat tidak memerlukan API atau token, tetapi operator tetap harus menekan tombol Kirim di WhatsApp. Cloud API mengirim di latar belakang dan memerlukan konfigurasi Meta.</small></div><div class="notice" id="whatsappModeStatus">Metode aktif: ${settings.waDeliveryMode==='click_to_chat'?'Click-to-Chat':'WhatsApp Cloud API'}.</div><div class="actions"><button class="btn" id="saveWhatsAppMode">Simpan Metode Pengiriman</button></div><hr><h3>Konfigurasi WhatsApp Cloud API</h3><p class="muted">Isi bagian ini hanya jika memilih WhatsApp Cloud API.</p><div class="notice" id="whatsappCloudStatus">Memeriksa konfigurasi WhatsApp Cloud API…</div><div class="form-grid"><div class="field"><label>WhatsApp Phone Number ID</label><input id="waPhoneNumberId" inputmode="numeric" placeholder="ID nomor dari Meta"></div><div class="field"><label>Graph API Version</label><input id="waApiVersion" value="v26.0" placeholder="v26.0"></div><div class="field" style="grid-column:1/-1"><label>WhatsApp Access Token</label><input id="waAccessToken" type="password" autocomplete="new-password" placeholder="Tempel token permanen / token sistem dari Meta"></div><div class="field"><label>Nama Template Utility yang disetujui</label><input id="waTemplateName" value="kaca_hasil_photobooth" placeholder="kaca_hasil_photobooth"></div><div class="field"><label>Bahasa Template</label><input id="waTemplateLanguage" value="id" placeholder="id"></div></div><small class="field-help">Buat dan setujui template Utility di WhatsApp Manager. Template harus memiliki tepat satu variabel teks {{1}} pada isi pesan untuk link folder Drive. Access Token disimpan lokal pada komputer booth dan tidak ditampilkan kembali.</small><div class="actions wrap"><button class="btn" id="saveWhatsAppCloud">Simpan Konfigurasi WhatsApp</button><button class="btn secondary" id="retryWhatsAppJobs">Periksa Antrean WhatsApp</button></div><div class="notice" id="whatsappCloudJobs">Antrean pesan akan ditampilkan di sini.</div></div><div class="panel"><div class="eyebrow2">KACA.ID / DIAGNOSTIK</div><h3>App Logs · Catatan Permasalahan</h3><p class="muted">Lihat catatan error aplikasi, backend kamera, dan kondisi renderer ketika aplikasi mengalami bug, macet, atau crash. Log disimpan lokal dengan rotasi ukuran agar tidak terus membesar.</p><div class="actions wrap"><button class="btn secondary" id="refreshAppLogs">Muat Ulang Log</button><button class="btn secondary" id="openAppLogsFolder">Buka Folder Log</button><button class="btn secondary" id="clearAppLogs">Bersihkan Log</button></div><pre id="appLogsViewer" class="app-logs-viewer" aria-live="polite">Memuat catatan aplikasi…</pre><small class="field-help">Lokasi: folder data pengguna KACA.ID / logs. Maksimum sekitar 8 MB untuk empat file log. Sebelum membagikan log, periksa dan samarkan informasi pribadi.</small></div><div class="panel"><div class="eyebrow2">KACA.ID / DASHBOARD MODES</div><h3>Mode yang Ditampilkan di Dasbor</h3><p class="muted">Nonaktifkan mode yang tidak ingin digunakan. Tombol yang dinonaktifkan tidak akan muncul di dasbor.</p><div class="form-grid"><label class="frame-enable-check"><input id="enablePhotoMode" type="checkbox" ${settings.enablePhotoMode!==false?'checked':''}><span>Tampilkan mode PHOTO di dasbor</span></label><label class="frame-enable-check"><input id="enableVideoMode" type="checkbox" ${settings.enableVideoMode!==false?'checked':''}><span>Tampilkan mode VIDEO di dasbor</span></label></div><div class="actions"><button class="btn" id="saveDashboardModes">Simpan Mode Dasbor</button></div><div class="notice" id="dashboardModesStatus">Mode aktif: ${settings.enablePhotoMode!==false?'PHOTO ':''}${settings.enableVideoMode!==false?'VIDEO':''}.</div></div><div class="panel"><div class="eyebrow2">KACA.ID / GENERAL QUALITY</div><h3>Kualitas Foto, Video & Cetakan</h3><div class="form-grid"><div class="field"><label>Kualitas foto JPEG (%)</label><input id="generalJpeg" type="number" min="60" max="100" value="${settings.jpegQuality??100}"></div><div class="field"><label>Kualitas video Live Photo</label><select id="generalVideoQuality"><option value="high">Tinggi · kualitas utama</option><option value="balanced">Seimbang · file lebih kecil</option><option value="compact">Hemat ruang</option></select></div><div class="field"><label>Durasi mode Video (detik)</label><input id="generalVideoDuration" type="number" min="5" max="300" value="${settings.videoDurationSeconds||30}"><small class="field-help">Durasi otomatis 5–300 detik. Operator juga dapat menghentikan rekaman lebih awal.</small></div><div class="field"><label>DPI cetakan</label><select id="generalDpi"><option value="300">300 DPI</option><option value="600">600 DPI</option></select></div></div><small class="field-help">KACA.ID tidak mengecilkan frame sumber saat menyimpan. JPEG menggunakan kualitas sesuai nilai ini. Catatan Canon: build EDSDK saat ini masih memakai frame Live View untuk foto; transfer file JPEG/RAW asli resolusi penuh dari kamera belum tersedia dan perlu implementasi transfer EDSDK tersendiri.</small><div class="actions"><button class="btn" id="saveGeneralQuality">Simpan Kualitas</button></div><div class="notice" id="generalQualityStatus">Pengaturan kualitas foto, video, dan cetakan.</div></div>
 <div class="panel"><div class="eyebrow2">KACA.ID / CAMERA STUDIO</div><h3>Pengaturan Kamera</h3><label class="frame-enable-check"><input id="multicamEnabled" type="checkbox" ${settings.multicamEnabled?'checked':''}><span>Aktifkan fitur MultiCam (2 kamera)</span></label><div class="actions wrap"><button class="btn secondary" id="detectCamera1">Deteksi Kamera 1</button><button class="btn secondary" id="detectCamera2">Deteksi Kamera 2</button></div><div class="form-grid"><div class="field"><label>Kamera Angle 1 (utama)</label><select id="multiCamera1"><option value="">Pilih kamera</option>${opts}</select></div><div class="field"><label>Kamera Angle 2 (kedua)</label><select id="multiCamera2"><option value="">Pilih kamera kedua</option>${opts}</select></div></div><div class="multicam-preview-grid"><div class="camera-preview"><b>PREVIEW ANGLE 1</b><div class="kaca-camera-image-stage"><img id="multiPreview1" alt="Preview kamera utama"></div><button class="btn secondary multicam-preview-toggle" id="showMultiPreview1">Tampilkan Preview Kamera 1</button></div><div class="camera-preview"><b>PREVIEW ANGLE 2</b><div class="kaca-camera-image-stage"><img id="multiPreview2" alt="Preview kamera kedua"></div><button class="btn secondary multicam-preview-toggle" id="showMultiPreview2">Tampilkan Preview Kamera 2</button></div></div><div class="actions"><button class="btn secondary" id="openMultiCams">Aktifkan / Hubungkan Kamera</button><button class="btn" id="saveMultiCams">Simpan Konfigurasi MultiCam</button></div><div class="notice" id="multiStatus">Deteksi Kamera 1 dan Kamera 2 secara terpisah. Kamera kedua harus merupakan perangkat berbeda dari kamera pertama.</div><p class="muted">Setiap tombol deteksi memeriksa webcam, kamera bawaan, dan Canon EOS USB melalui EDSDK. Canon dapat digunakan pada salah satu angle; satu unit Canon yang sama tidak dapat dipakai pada dua angle sekaligus.</p><p></p>
 <h3 style="margin-top:22px">Orientasi & Flip Kamera</h3><p class="muted">Rotasi dan flip diterapkan konsisten pada live preview, foto sesi, serta Live Photo. Pengaturan ini tidak mengubah setelan fisik kamera DSLR.</p><div class="form-grid">${[1,2].map(slot=>`<div class="kaca-orientation-card"><h4>Kamera ${slot} · Angle ${slot}</h4><div class="field"><label>Rotasi Kamera ${slot}</label><select id="cameraRotation${slot}"><option value="0">0° · Normal</option><option value="90">90° · Putar kanan</option><option value="180">180° · Terbalik</option><option value="270">270° · Putar kiri</option></select></div><label class="frame-enable-check"><input id="cameraFlipHorizontal${slot}" type="checkbox"> Flip horizontal kamera ${slot}</label><label class="frame-enable-check"><input id="cameraFlipVertical${slot}" type="checkbox"> Flip vertikal kamera ${slot}</label></div>`).join('')}</div><div class="actions"><button class="btn" id="saveCameraOrientation">Simpan Orientasi Kamera</button></div><div class="notice" id="cameraOrientationStatus">Orientasi hanya diterapkan pada tampilan dan hasil sesi berikutnya.</div><hr><h3>Pengaturan Kualitas Live Preview</h3><p class="muted">Pengaturan berikut hanya memengaruhi tampilan live di aplikasi. Tidak mengubah foto asli, hasil lokal, file Google Drive, exposure/ISO kamera, maupun kualitas cetak.</p><div class="form-grid"><div class="field"><label>Kualitas gambar preview JPEG</label><select id="livePreviewQuality"><option value="50">Hemat · 50%</option><option value="65">Seimbang · 65%</option><option value="76">Standar · 76%</option><option value="85">Tinggi · 85%</option><option value="92">Sangat tinggi · 92%</option></select></div><div class="field"><label>Kecerahan tampilan preview</label><input id="livePreviewBrightness" type="range" min="70" max="130" step="5" value="${settings.livePreviewBrightness??100}"><small class="field-help"><span id="livePreviewBrightnessValue">${settings.livePreviewBrightness??100}%</span> · hanya tampilan</small></div><div class="field"><label>FPS live preview</label><select id="livePreviewFps"><option value="5">5 FPS · sangat ringan</option><option value="10">10 FPS · hemat</option><option value="15">15 FPS · standar</option><option value="20">20 FPS</option><option value="24">24 FPS</option><option value="30">30 FPS · lebih halus</option></select></div></div><div class="actions"><button class="btn" id="saveLivePreviewSettings">Simpan Kualitas Preview</button></div><div class="notice" id="livePreviewSettingsStatus">Pengaturan preview tidak mengubah file foto dan video yang disimpan.</div><hr> <h3 style="margin-top:22px">Kontrol Profesional Tiap Kamera</h3><p class="muted">Slider tersedia di bawah preview Kamera 1 dan Kamera 2. Nilai diambil dari driver saat kamera aktif; kontrol yang tidak tersedia dinonaktifkan. Setelan DSLR yang tidak didukung OpenCV tidak dipaksakan.</p></div>`;
 const loadAppLogs=async()=>{const viewer=$('#appLogsViewer');try{const lines=await window.kaca.readAppLogs();viewer.textContent=(lines||[]).join('\n')||'Belum ada catatan log. Error baru akan muncul di sini.';viewer.scrollTop=viewer.scrollHeight;}catch(e){viewer.textContent='Gagal membaca log: '+e.message;}};
 $('#refreshAppLogs').onclick=loadAppLogs;
 $('#openAppLogsFolder').onclick=()=>window.kaca.openAppLogs();
 $('#clearAppLogs').onclick=async()=>{if(!(await kacaConfirm('Hapus catatan log yang tersimpan?')))return;await window.kaca.clearAppLogs();await loadAppLogs();};
 loadAppLogs();
 $('#chooseLocalStorage').onclick=async()=>{const p=await window.kaca.chooseStorageFolder();if(p){$('#localStoragePath').value=p;$('#localStorageStatus').textContent='Folder dipilih. Tekan Simpan Lokasi untuk menerapkan.';}};
 const refreshDriveStatus=async()=>{const d=await api('/api/google-drive/status');$('#googleDriveStatus').textContent=d.connected?'Google Drive terhubung'+(d.account_email?' · '+d.account_email:'')+'. Upload otomatis aktif.':(d.configured?'Client OAuth tersimpan, akun belum terhubung.':'Google Drive belum dikonfigurasi.');const pending=(d.jobs||[]).filter(j=>['waiting_auth','pending','uploading','error'].includes(j.status));$('#googleDriveJobs').textContent=pending.length+' unggahan menunggu atau sedang diproses.';return d;};
 $('#connectGoogleDrive').onclick=async()=>{const btn=$('#connectGoogleDrive');try{btn.disabled=true;btn.textContent='Menyimpan…';await api('/api/google-drive/config',{method:'POST',body:JSON.stringify({client_id:$('#googleDriveClientId').value.trim(),client_secret:$('#googleDriveClientSecret').value.trim()})});const auth=await api('/api/google-drive/auth-url',{method:'POST',body:'{}'});await window.kaca.openExternal(auth.url);$('#googleDriveStatus').textContent='Halaman Google terbuka. Masuk ke akun booth dan izinkan akses Google Drive, lalu kembali ke KACA.ID.';let tries=0;const poll=setInterval(async()=>{tries++;try{const d=await refreshDriveStatus();if(d.connected||tries>=90)clearInterval(poll);}catch(e){if(tries>=90)clearInterval(poll);}},2000);}catch(e){$('#googleDriveStatus').textContent='Gagal menghubungkan Google Drive: '+e.message;}finally{btn.disabled=false;btn.textContent='Simpan & Hubungkan Google Drive';}};
 $('#retryGoogleDrive').onclick=async()=>{try{const r=await api('/api/google-drive/retry',{method:'POST',body:'{}'});$('#googleDriveStatus').textContent=r.queued+' unggahan dimasukkan kembali ke antrean.';await refreshDriveStatus();}catch(e){$('#googleDriveStatus').textContent='Gagal mengulang upload: '+e.message;}};
 $('#disconnectGoogleDrive').onclick=async()=>{if(!(await kacaConfirm('Putuskan akun Google Drive pada komputer ini? Unggahan baru akan menunggu sampai akun dihubungkan kembali.')))return;try{await api('/api/google-drive/disconnect',{method:'POST',body:'{}'});await refreshDriveStatus();}catch(e){$('#googleDriveStatus').textContent='Gagal memutuskan akun: '+e.message;}};
 refreshDriveStatus().catch(()=>{});
 const refreshWhatsAppStatus=async()=>{const w=await api('/api/whatsapp/status');$('#whatsappCloudStatus').textContent=w.configured?'WhatsApp Cloud API sudah dikonfigurasi · '+w.phone_number_id+' · Template '+w.template_name:'WhatsApp Cloud API belum dikonfigurasi.';$('#waPhoneNumberId').value=w.phone_number_id||'';$('#waApiVersion').value=w.api_version||'v26.0';$('#waTemplateName').value=w.template_name||'kaca_hasil_photobooth';$('#waTemplateLanguage').value=w.language||'id';$('#waAccessToken').placeholder=w.token_saved?'Token tersimpan. Kosongkan untuk memakai token yang sama.':'Masukkan Access Token dari Meta';const jobs=w.jobs||[];const pending=jobs.filter(j=>['waiting_drive','pending','sending'].includes(j.status)).length;$('#whatsappCloudJobs').textContent=jobs.length+' antrean terakhir · '+pending+' menunggu/diproses.';return w;};
 $('#saveWhatsAppCloud').onclick=async()=>{const b=$('#saveWhatsAppCloud');try{b.disabled=true;b.textContent='Menyimpan…';const w=await api('/api/whatsapp/config',{method:'POST',body:JSON.stringify({phone_number_id:$('#waPhoneNumberId').value.trim(),access_token:$('#waAccessToken').value.trim(),api_version:$('#waApiVersion').value.trim(),template_name:$('#waTemplateName').value.trim(),language:$('#waTemplateLanguage').value.trim()})});$('#waAccessToken').value='';$('#whatsappCloudStatus').textContent='Konfigurasi WhatsApp tersimpan di komputer booth.';await refreshWhatsAppStatus();}catch(e){$('#whatsappCloudStatus').textContent='Gagal menyimpan konfigurasi: '+e.message;}finally{b.disabled=false;b.textContent='Simpan Konfigurasi WhatsApp';}};
 $('#retryWhatsAppJobs').onclick=async()=>{try{const w=await refreshWhatsAppStatus();$('#whatsappCloudJobs').textContent='Status antrean diperbarui. '+(w.jobs||[]).length+' antrean terakhir.';}catch(e){$('#whatsappCloudJobs').textContent='Gagal membaca antrean: '+e.message;}};
 $('#saveWhatsAppMode').onclick=async()=>{const b=$('#saveWhatsAppMode'),notice=$('#whatsappModeStatus');try{b.disabled=true;b.textContent='Menyimpan…';settings.waDeliveryMode=$('#waDeliveryMode').value;await saveScopedSettings();notice.textContent='Metode tersimpan: '+(settings.waDeliveryMode==='click_to_chat'?'Click-to-Chat':settings.waDeliveryMode==='gateway_fonnte'?'Gateway Fonnte':'WhatsApp Cloud API')+'.';}catch(e){notice.textContent='Gagal menyimpan metode WhatsApp: '+e.message;}finally{b.disabled=false;b.textContent='Simpan Metode Pengiriman';}};
 $('#content').insertAdjacentHTML('beforeend',`<div class="panel"><h3>Gateway Fonnte — Tanpa WhatsApp Cloud API langsung</h3><p class="muted">Saat pelanggan menyetujui dan menekan tombol kirim, KACA.ID mengirim tautan melalui API gateway Fonnte tanpa membuka WhatsApp Web. Memerlukan <b>token perangkat (Devices → Token)</b>, bukan token akun di menu Settings. Perangkat WhatsApp pada Fonnte harus terhubung. Jika muncul invalid token, salin ulang token perangkat tersebut. Jangan tambahkan awalan Bearer. Pengiriman otomatis tidak dijamin oleh WhatsApp dan bisa terpengaruh kebijakan platform.</p><div class="field"><label>Nomor WhatsApp akun pengirim Fonnte</label><input id="fonnteSenderNumber" inputmode="tel" value="${esc(settings.fonnteSenderNumber||'+62 823-9667-4553')}" placeholder="+62 823-9667-4553"><small class="field-help">Nomor akun Anda. Nomor ini bersifat identitas tampilan; koneksi sebenarnya ditentukan oleh perangkat dan token Fonnte yang valid.</small></div><div class="field"><label>Token API Fonnte</label><input id="fonnteToken" type="password" autocomplete="new-password" placeholder="Token API perangkat Fonnte"></div><div class="actions"><button class="btn" id="saveFonnteToken">Simpan Token Gateway</button></div><div class="notice" id="fonnteGatewayStatus">Memeriksa gateway…</div><small class="field-help">Status diterima API bukan bukti pesan sudah diterima nomor pelanggan. Gunakan hanya untuk pelanggan yang menyetujui menerima pesan.</small></div>`);
 $('#content').insertAdjacentHTML('beforeend',`<div class="panel kaca-fonnte-check"><h3>Diagnostik Koneksi Fonnte</h3><p class="muted">Periksa apakah token berlaku, perangkat WhatsApp terhubung, dan kuota masih tersedia. Token tidak ditampilkan.</p><div class="actions wrap"><button class="btn secondary" id="checkFonnteDevice" type="button">Periksa Koneksi &amp; Kuota Fonnte</button><button class="btn" id="activateFonnteMode" type="button">Aktifkan Pengiriman Fonnte</button></div><div class="notice" id="fonnteDeviceResult">Belum diperiksa.</div></div>`);
 $('#activateFonnteMode').onclick=async()=>{const btn=$('#activateFonnteMode');btn.disabled=true;try{const st=await api('/api/whatsapp/fonnte/status');if(!st.configured)throw new Error('Simpan token Fonnte terlebih dahulu.');settings.waDeliveryMode='gateway_fonnte';await saveScopedSettings();if($('#waDeliveryMode'))$('#waDeliveryMode').value='gateway_fonnte';$('#fonnteDeviceResult').textContent='Pengiriman melalui Fonnte aktif. Tekan Periksa Koneksi untuk memastikan perangkat WhatsApp terhubung.';}catch(e){$('#fonnteDeviceResult').textContent='Gagal mengaktifkan: '+e.message;}finally{btn.disabled=false;}};
 $('#checkFonnteDevice').onclick=async()=>{const button=$('#checkFonnteDevice'),target=$('#fonnteDeviceResult');button.disabled=true;target.textContent='Menghubungi Fonnte…';try{const profile=await api('/api/whatsapp/fonnte/device');target.textContent='Perangkat: '+(profile.device||'-')+' · Koneksi: '+(profile.device_status||'tidak diketahui')+' · Kuota: '+(profile.quota??'tidak tersedia')+' · Paket: '+(profile.package||'-')+(profile.warning?' · '+profile.warning:'');}catch(error){target.textContent='Pemeriksaan gagal: '+error.message+' — Periksa token dan koneksi perangkat di dashboard Fonnte.';}finally{button.disabled=false;}};
 api('/api/whatsapp/fonnte/status').then(x=>{$('#fonnteGatewayStatus').textContent=x.configured?'Token Fonnte tersimpan. Pilih Gateway Fonnte pada Metode Pengiriman.':'Fonnte belum dikonfigurasi.';$('#fonnteToken').placeholder=x.configured?'Token tersimpan; kosongkan untuk memakai token lama':'Masukkan token Fonnte';}).catch(e=>{$('#fonnteGatewayStatus').textContent=e.message;});
 $('#saveFonnteToken').onclick=async()=>{const button=$('#saveFonnteToken');try{button.disabled=true;const r=await api('/api/whatsapp/fonnte/config',{method:'POST',body:JSON.stringify({token:$('#fonnteToken').value.trim()})});$('#fonnteToken').value='';if(r.configured){settings.fonnteSenderNumber=$('#fonnteSenderNumber').value.trim();settings.waDeliveryMode='gateway_fonnte';await saveScopedSettings();if($('#waDeliveryMode'))$('#waDeliveryMode').value='gateway_fonnte';}$('#fonnteGatewayStatus').textContent=r.configured?'Token disimpan, mode Gateway Fonnte otomatis diaktifkan. Klik Periksa Koneksi untuk memastikan perangkat dan kuota.':'Belum berhasil menyimpan token.';}catch(e){$('#fonnteGatewayStatus').textContent='Gagal: '+e.message;}finally{button.disabled=false;}};

 refreshWhatsAppStatus().catch(()=>{});
 $('#saveLocalStorage').onclick=async()=>{const p=$('#localStoragePath').value.trim();try{const requested=(!p||p.includes('(default)'))?'':p;const r=await api('/api/storage/location',{method:'POST',body:JSON.stringify({path:requested})});settings.localStoragePath=requested?r.path:'';}catch(e){$('#localStorageStatus').textContent='Gagal mengatur folder: '+e.message;return;}await saveScopedSettings();$('#localStorageStatus').textContent='Lokasi penyimpanan berhasil diterapkan untuk sesi berikutnya: '+(settings.localStoragePath||'Pictures\\KACA STUDIO');};
 $('#generalDpi').value=String(settings.printDpi||300);$('#generalVideoQuality').value=settings.videoQuality||'high';$('#generalVideoDuration').value=String(settings.videoDurationSeconds||30);for(const slot of [1,2]){
   const suffix=slot===1?'':'2';
   $('#cameraRotation'+slot).value=String(settings['cameraRotation'+suffix]??0);
   $('#cameraFlipHorizontal'+slot).checked=!!settings['cameraFlipHorizontal'+suffix];
   $('#cameraFlipVertical'+slot).checked=!!settings['cameraFlipVertical'+suffix];
 }$('#livePreviewQuality').value=String(settings.livePreviewQuality??76);$('#livePreviewBrightness').value=String(settings.livePreviewBrightness??100);$('#livePreviewFps').value=String(settings.livePreviewFps??15);$('#livePreviewBrightness').oninput=()=>$('#livePreviewBrightnessValue').textContent=$('#livePreviewBrightness').value+'%';const primarySelect=$('#multiCamera1'),secondarySelect=$('#multiCamera2'),preferredPrimary=String(settings.cameraDeviceId||(settings.cameraDevice??1)),preferredSecondary=settings.multicamCamera2==null?'':String(settings.multicamCamera2);if([...primarySelect.options].some(o=>o.value===preferredPrimary))primarySelect.value=preferredPrimary;else if(primarySelect.options.length>1)primarySelect.selectedIndex=1;if(preferredSecondary!==primarySelect.value&&[...secondarySelect.options].some(o=>o.value===preferredSecondary))secondarySelect.value=preferredSecondary;
 const refreshCameraList=async()=>{await api('/api/cameras');let st={};for(let i=0;i<90;i++){await new Promise(r=>setTimeout(r,350));st=await api('/api/status');if(st.scan_done)break;}const list=st.cameras||[];let canon=[];try{const cr=await api('/api/canon/detect');canon=cr.cameras||[];}catch(e){}const devices=[...list.map(c=>({id:String(c.id),label:c.label,kind:'opencv'})),...canon.map(c=>({id:String(c.id),label:`${c.name||'Canon EOS'} · USB / EDSDK`,kind:'canon'}))];for(const id of ['multiCamera1','multiCamera2']){const el=$('#'+id),old=el.value,preferred=id==='multiCamera1'?String(settings.cameraDeviceId||(settings.cameraDevice??1)):String(settings.multicamCamera2??'');el.innerHTML=(id==='multiCamera1'?'<option value="">Pilih kamera</option>':'<option value="">Pilih kamera kedua</option>')+devices.map(c=>`<option value="${c.id}">${c.label}</option>`).join('');if([...el.options].some(o=>o.value===old))el.value=old;else if(preferred&&[...el.options].some(o=>o.value===preferred))el.value=preferred;}return devices;};
 const detectSlot=async(slot)=>{const status=$('#multiStatus');const button=$('#detectCamera'+slot);button.disabled=true;status.textContent=`Memindai webcam, kamera bawaan, dan Canon EDSDK untuk Kamera ${slot}…`;try{const devices=await refreshCameraList();if(!devices.length)throw new Error('Tidak ada kamera yang dapat dideteksi. Periksa sambungan USB dan izin kamera.');const primary=$('#multiCamera1'),secondary=$('#multiCamera2'),target=slot===1?primary:secondary,other=slot===1?secondary:primary;let chosen;if(slot===1){chosen=devices.find(c=>c.id===String(settings.cameraDeviceId||settings.cameraDevice))||devices.find(c=>c.id==='1')||devices[0];}else{chosen=devices.find(c=>c.id!==other.value&&c.id===String(settings.multicamCamera2))||devices.find(c=>c.id!==other.value);if(!chosen)throw new Error('Tidak ditemukan perangkat kedua yang berbeda dari Kamera 1.');}target.value=chosen.id;if(other.value===chosen.id)other.value='';if(slot===1){settings.cameraDeviceId=chosen.id;if(!chosen.id.startsWith('canon_edsdk_'))settings.cameraDevice=Number(chosen.id);}else{settings.multicamCamera2=chosen.id;}await saveScopedSettings();status.textContent=`Kamera ${slot} terdeteksi: ${chosen.label}. ${devices.length} perangkat tersedia.`;}catch(e){status.textContent=`Deteksi Kamera ${slot} gagal: ${e.message}`;}finally{button.disabled=false;}};
 $('#detectCamera1').onclick=()=>detectSlot(1);$('#detectCamera2').onclick=()=>detectSlot(2);
 $('#saveDashboardModes').onclick=async()=>{settings.enablePhotoMode=$('#enablePhotoMode').checked;settings.enableVideoMode=$('#enableVideoMode').checked;await saveScopedSettings();$('#dashboardModesStatus').textContent='Pengaturan mode dasbor berhasil disimpan.';};
 $('#saveGeneralQuality').onclick=async()=>{settings.jpegQuality=Math.max(60,Math.min(100,Number($('#generalJpeg').value)||100));settings.videoQuality=$('#generalVideoQuality').value;settings.videoDurationSeconds=Math.max(5,Math.min(300,Number($('#generalVideoDuration').value)||30));settings.printDpi=Number($('#generalDpi').value);await saveScopedSettings();$('#generalQualityStatus').textContent='Kualitas foto tersimpan. Foto sumber tidak diubah ukurannya; JPEG disimpan pada kualitas sesuai nilai yang dipilih.';};
 const connectMultiCamera=async(slot)=>{const id=$('#multiCamera'+slot).value;if(!id)throw new Error(`Pilih Kamera ${slot} terlebih dahulu.`);if(slot===1){const r=id.startsWith('canon_edsdk_')?await api('/api/canon/open',{method:'POST',body:JSON.stringify({id})}):await api('/api/camera/open',{method:'POST',body:JSON.stringify({index:Number(id)})});if(!r.ok&&r.camera_open!==true)throw new Error(r.error||'Kamera 1 gagal diaktifkan.');}else{const r=id.startsWith('canon_edsdk_')?await api('/api/camera/secondary/canon/open',{method:'POST',body:JSON.stringify({id})}):await api('/api/camera/secondary/open',{method:'POST',body:JSON.stringify({index:Number(id)})});if(!r.ok)throw new Error(r.error||'Kamera 2 gagal diaktifkan.');}return id;};
 const showMultiPreview=async(slot)=>{const btn=$('#showMultiPreview'+slot),img=$('#multiPreview'+slot);btn.disabled=true;try{await connectMultiCamera(slot);img.src=`http://127.0.0.1:8765/${slot===1?'api/stream.mjpg':'api/stream-secondary.mjpg'}?preview=${Date.now()}&quality=${Number(settings.livePreviewQuality??76)}&fps=${Number(settings.livePreviewFps??15)}`;img.style.filter=`brightness(${Number(settings.livePreviewBrightness??100)}%)`;updatePreviewVisuals();img.style.display='block';updatePreviewVisuals();img.onload=()=>{$('#multiStatus').textContent=`Preview Kamera ${slot} tampil.`;};img.onerror=()=>{$('#multiStatus').textContent=`Kamera ${slot} aktif tetapi stream preview belum tersedia.`;};if(slot===2)settings.multicamCamera2Ready=true;else settings.cameraDeviceId=$('#multiCamera1').value;await saveScopedSettings();}catch(e){$('#multiStatus').textContent=`Preview Kamera ${slot} gagal: ${e.message}`;}finally{btn.disabled=false;void loadCameraCapabilities(slot).catch(error=>console.warn('[KACA_CAMERA_CONTROLS]',error));}};
 $('#showMultiPreview1').onclick=()=>showMultiPreview(1);$('#showMultiPreview2').onclick=()=>showMultiPreview(2);
 $('#openMultiCams').onclick=async()=>{try{const first=$('#multiCamera1').value,second=$('#multiCamera2').value;if(!first||!second)throw new Error('Deteksi dan pilih Kamera 1 serta Kamera 2 terlebih dahulu.');if(first===second)throw new Error('Kamera 1 dan Kamera 2 harus perangkat berbeda.');await connectMultiCamera(1);await connectMultiCamera(2);settings.multicamCamera2Ready=true;settings.cameraDeviceId=first;if(!first.startsWith('canon_edsdk_'))settings.cameraDevice=Number(first);settings.multicamCamera2=second;await saveScopedSettings();$('#multiStatus').textContent='Kedua kamera berhasil diaktifkan. Gunakan tombol di bawah masing-masing layar untuk menampilkan preview.';}catch(e){$('#multiStatus').textContent='MultiCam gagal diaktifkan: '+e.message;settings.multicamCamera2Ready=false;}};
 $('#saveMultiCams').onclick=async()=>{settings.multicamEnabled=$('#multicamEnabled').checked;const first=$('#multiCamera1').value,second=$('#multiCamera2').value;if(settings.multicamEnabled&&(!first||!second)){$('#multiStatus').textContent='Pilih Kamera 1 dan Kamera 2 terlebih dahulu.';return;}if(settings.multicamEnabled&&second&&first===second){$('#multiStatus').textContent='Kamera 1 dan Kamera 2 harus perangkat berbeda.';return;}if(first){settings.cameraDeviceId=first;if(!first.startsWith('canon_edsdk_'))settings.cameraDevice=Number(first);}settings.multicamCamera2=second||null;settings.multicamCamera2Ready=!!(settings.multicamEnabled&&settings.multicamCamera2Ready);settings.activeCameraAngle=0;if(!settings.multicamEnabled){await api('/api/camera/secondary/close',{method:'POST',body:'{}'}).catch(()=>{});settings.multicamCamera2Ready=false;}await saveScopedSettings();$('#multiStatus').textContent=settings.multicamEnabled?'MultiCam aktif. Pilihan ANGLE 1/ANGLE 2 akan tampil di sesi foto.':'MultiCam nonaktif; hanya kamera utama yang digunakan.';};
 $('#saveCameraOrientation').onclick=async()=>{for(const slot of [1,2]){
    const suffix=slot===1?'':'2';
    settings['cameraRotation'+suffix]=Number($('#cameraRotation'+slot).value)||0;
    settings['cameraFlipHorizontal'+suffix]=$('#cameraFlipHorizontal'+slot).checked;
    settings['cameraFlipVertical'+suffix]=$('#cameraFlipVertical'+slot).checked;
   }await saveScopedSettings();updatePreviewVisuals();
   $('#cameraOrientationStatus').textContent='Orientasi Kamera 1 dan Kamera 2 tersimpan secara terpisah untuk sesi berikutnya.';};
 $('#saveLivePreviewSettings').onclick=async()=>{settings.livePreviewQuality=Number($('#livePreviewQuality').value)||76;settings.livePreviewBrightness=Number($('#livePreviewBrightness').value)||100;settings.livePreviewFps=Number($('#livePreviewFps').value)||15;await saveScopedSettings();$('#livePreviewSettingsStatus').textContent=`Tersimpan: kualitas ${settings.livePreviewQuality}%, kecerahan ${settings.livePreviewBrightness}%, ${settings.livePreviewFps} FPS. Hanya memengaruhi live preview.`;};
 // Keep both camera previews updated without a second "Tampilkan Preview" click.
 let activeCameraPreviewBusy=false;
 const previewCameraAutomatically=async()=>{
   if(activeCameraPreviewBusy||window.kacaCurrentMenu!=='generalSettings')return;
   activeCameraPreviewBusy=true;
   try{
     const id=$('#multiCamera1')?.value;if(id)await showMultiPreview(1);
     const second=$('#multiCamera2')?.value;
     if(second)await showMultiPreview(2);
   }finally{activeCameraPreviewBusy=false;}
 };
 const clearCameraPreview=()=>{
   for(const n of [1,2]){const image=$('#multiPreview'+n);if(image){image.removeAttribute('src');image.style.display='none';}}
 };
 window.kacaCameraPreviewStop=()=>{clearCameraPreview();if(typeof previewResizeObserver!=='undefined')previewResizeObserver?.disconnect();};
 for(const slot of [1,2]){
   $('#multiCamera'+slot).addEventListener('change',()=>{
     const image=$('#multiPreview'+slot);if(image)image.removeAttribute('src');
     if(window.kacaGeneralSettingsTab==='camera')void showMultiPreview(slot).then(()=>loadCameraCapabilities(slot)).catch(()=>{});
   });
 }
 const controlDefinitions=[
  ['brightness','Brightness'],['contrast','Kontras'],['saturation','Saturasi'],
  ['exposure','Exposure / Shutter'],['iso','ISO'],['gain','Gain'],
  ['focus','Fokus'],['white_balance','White Balance'],['sharpness','Sharpness']
 ];
 const cameraLastConfirmedControls={1:{},2:{}};
 // Only an explicitly stored good-state profile is trusted as a reset baseline.
 const cameraProfileKey=slot=>'cameraNormalProfile'+slot;
 const cameraSliderTimers={1:{},2:{}};
 const loadCameraCapabilities=async(slot)=>{
   const container=$('#kacaCameraControls'+slot);if(!container)return;
   const selected=$('#multiCamera'+slot)?.value||'';
   // A webcam can already stream while its dropdown is empty after startup.
   // Detect active capture through backend rather than trusting the selector.
   let activeStatus={};
   try{activeStatus=await api('/api/status');}catch{}
   const isOpen=slot===1?!!activeStatus.camera_open:!!activeStatus.secondary_camera_open;
   const canonActive=slot===1?String(activeStatus.backend||'').includes('Canon EDSDK'):String(activeStatus.secondary_backend||'').includes('Canon EDSDK');
   if(!selected&&!isOpen){
     container.innerHTML='<h4>Kontrol Profesional · Kamera '+slot+'</h4><p class="muted">Kamera belum aktif. Hubungkan melalui pilihan perangkat di atas untuk menampilkan slider.</p><button type="button" class="btn secondary" id="retryCameraCapabilities'+slot+'">Periksa Ulang Kamera</button>';
     container.querySelector('button').onclick=()=>loadCameraCapabilities(slot);return;
   }
   if(selected.startsWith('canon_edsdk_')||canonActive){
     container.innerHTML='<h4>Kontrol Kamera DSLR Canon</h4><p class="muted">Kontrol ISO, shutter, white balance dan fokus dari Canon EDSDK belum tersedia dalam build ini. Gunakan kontrol pada kamera DSLR; tidak ada slider palsu yang bisa merusak setelan.</p>';
     return;
   }
   let response;
   try{response=await api('/api/camera/controls/capabilities?camera='+(slot-1));}
   catch(error){container.innerHTML='<p class="notice">Gagal membaca kemampuan kamera: '+esc(error.message)+'</p>';return;}
   if(!response.open){container.innerHTML='<h4>Kontrol Profesional · Kamera '+slot+'</h4><p class="notice">Stream tampak aktif, tetapi handle webcam belum dapat diakses untuk kontrol driver. Periksa pilihan kamera atau hubungkan ulang tanpa menutup aplikasi.</p><button type="button" class="btn secondary" id="retryCameraCapabilities'+slot+'">Periksa Ulang</button>';container.querySelector('button').onclick=()=>loadCameraCapabilities(slot);return;}
   const controls=response.controls||{};
   container.innerHTML=`<h4>Kontrol Profesional · Kamera ${slot}</h4><p class="muted">Geser perlahan. Nilai asli driver dibaca kembali. Rentang yang tidak disediakan driver adalah perkiraan dan bisa berbeda antar webcam.</p>`+
    controlDefinitions.map(([key,label])=>{
     const cap=controls[key]||{},actual=Number(cap.actual),available=!!cap.readable&&Number.isFinite(actual)&&cap.available!==false;
     const min=Number.isFinite(Number(cap.min))?Number(cap.min):0,
           max=Number.isFinite(Number(cap.max))?Number(cap.max):100,
           step=Number.isFinite(Number(cap.step))?Number(cap.step):1;
     if(available)cameraLastConfirmedControls[slot][key]=actual;
     const val=Number.isFinite(actual)?Math.min(max,Math.max(min,actual)):min;
     return `<div class="kaca-camera-ctl" data-camera-key="${key}"><label for="camDirect_${slot}_${key}">${label}<span class="kaca-ctl-actual">${available?actual.toFixed(2):'Tidak didukung'}</span></label><input id="camDirect_${slot}_${key}" type="range" min="${min}" max="${max}" step="${step}" value="${val}" ${available?'':'disabled'}><small class="field-help">${esc(cap.note||'Rentang berdasarkan pembacaan driver')}</small></div>`;
    }).join('')+`<div class="actions wrap"><button type="button" class="btn secondary" id="resetCamControls${slot}">Pulihkan Kontrol Webcam ${slot}</button><button type="button" class="btn secondary" id="recoverCamColor${slot}">Pulihkan Warna Webcam</button><button type="button" class="btn secondary" id="resetCamPreview${slot}">Reset Preview / Rotasi</button><button type="button" class="btn secondary" id="rememberCamNormal${slot}">Simpan Kondisi Normal</button></div><p class="notice" id="camDirectStatus${slot}">Nilai reset tidak lagi menggunakan nilai yang mungkin sudah gelap saat panel dibuka. Jika driver tidak menyediakan default yang pasti, pemulihan mencoba nilai netral secara aman dan melaporkan hasilnya.</p>`;
   for(const [key,label] of controlDefinitions){
     const slider=$('#camDirect_'+slot+'_'+key);if(!slider||slider.disabled)continue;
     const info=slider.closest('.kaca-camera-ctl').querySelector('.kaca-ctl-actual');
     slider.addEventListener('input',()=>{
       info.textContent=Number(slider.value).toFixed(2)+' · menerapkan';
       clearTimeout(cameraSliderTimers[slot][key]);
       cameraSliderTimers[slot][key]=setTimeout(async()=>{
         const desired=Number(slider.value),status=$('#camDirectStatus'+slot);
         try{
           const res=await api('/api/camera/controls',{method:'POST',body:JSON.stringify({camera:slot-1,values:{[key]:desired}})});
           const result=res.controls?.[key];
           if(!result?.supported || result.applied===false){
             const fallback=Number(result?.actual);
             if(Number.isFinite(fallback))slider.value=String(fallback);
             info.textContent='Ditolak driver';
             status.textContent=`${label}: perubahan ditolak atau nilai driver tidak sesuai. Setelan kamera tidak dianggap berhasil.`;
             return;
           }
           const actual=Number(result.actual);
           if(Number.isFinite(actual)){slider.value=String(actual);info.textContent=actual.toFixed(2);}
           else info.textContent=desired.toFixed(2);
           status.textContent=`${label} Kamera ${slot}: ${Number.isFinite(actual)?actual:desired}. Live preview menunjukkan hasil dari driver.`;
         }catch(error){info.textContent='Gagal';status.textContent=`${label}: ${error.message}`;}
       },350);
     });
   }
   const refreshCameraStatus=(res)=>{
     const status=$('#camDirectStatus'+slot);
     const success=Object.entries(res.controls||{}).filter(([,x])=>x.applied).map(([key])=>key);
     const rejected=Object.entries(res.controls||{}).filter(([,x])=>!x.applied).map(([key])=>key);
     // Never silently claim factory defaults when the backend only has estimates.
     const msg=(res.source==='saved_profile'?'Profil normal tersimpan diterapkan.':'Pemulihan nilai netral dicoba (bukan reset pabrik driver).')+
       (success.length?' Berhasil: '+success.join(', ')+'.':' Tidak ada perubahan yang diterima driver.')+
       (rejected.length?' Ditolak: '+rejected.join(', ')+'.':'')+
       ' Periksa gambar. Jika belum normal, gunakan panel pengaturan driver webcam Windows.';
     return msg;
   };
   const recoverCam=async(keys=null)=>{
     const status=$('#camDirectStatus'+slot);
     for(const timers of Object.values(cameraSliderTimers[slot]))clearTimeout(timers);
     status.textContent='Memulihkan kontrol Kamera '+slot+' dan membaca kembali nilai driver…';
     try{
       const saved=keys?null:(settings[cameraProfileKey(slot)]||null);
       const result=await api('/api/camera/controls/recover',{method:'POST',body:JSON.stringify({
         camera:slot-1,keys,profile:saved})});
       if(!result.ok)throw new Error(result.error||'Driver menolak pemulihan');
       const msg=refreshCameraStatus(result);
       await loadCameraCapabilities(slot);
       const note=$('#camDirectStatus'+slot);if(note)note.textContent=msg;
       return result;
     }catch(e){const note=$('#camDirectStatus'+slot);if(note)note.textContent='Pemulihan gagal: '+e.message;return null;}
   };
   $('#recoverCamColor'+slot).onclick=()=>recoverCam(['saturation','white_balance','auto_wb']);
   $('#rememberCamNormal'+slot).onclick=async()=>{
     const status=$('#camDirectStatus'+slot);
     try{
       const current=await api('/api/camera/controls/capabilities?camera='+(slot-1));
       if(!current.open)throw new Error('Kamera belum aktif');
       const profile={};
       for(const [key,cap] of Object.entries(current.controls||{})){
         if(cap.readable&&cap.available&&Number.isFinite(Number(cap.actual)))profile[key]=Number(cap.actual);
       }
       if(!Object.keys(profile).length)throw new Error('Driver tidak melaporkan nilai kontrol.');
       settings[cameraProfileKey(slot)]=profile;
       await saveScopedSettings();
       status.textContent='Profil kamera NORMAL disimpan dari kondisi saat ini. Setelah diubah, tombol Pulihkan akan mengembalikan nilai profil ini.';
     }catch(e){status.textContent='Gagal menyimpan profil normal: '+e.message;}
   };
   $('#resetCamPreview'+slot).onclick=async()=>{
     $('#cameraRotation'+slot).value='0';
     $('#cameraFlipHorizontal'+slot).checked=false;
     $('#cameraFlipVertical'+slot).checked=false;
     $('#livePreviewBrightness').value='100';
     settings['cameraRotation'+(slot===1?'':'2')]=0;
     settings['cameraFlipHorizontal'+(slot===1?'':'2')]=false;
     settings['cameraFlipVertical'+(slot===1?'':'2')]=false;
     settings.livePreviewBrightness=100;
     updatePreviewVisuals();
     const image=$('#multiPreview'+slot);
     if(image)image.style.filter='none';
     try{await saveScopedSettings();$('#camDirectStatus'+slot).textContent='Transformasi preview direset. Kontrol hardware kamera tidak diubah. Untuk brightness/warna kamera, tekan Pulihkan Kontrol Webcam.';}
     catch(e){$('#camDirectStatus'+slot).textContent='Preview reset sementara, gagal menyimpan: '+e.message;}
   };
   $('#resetCamControls'+slot).onclick=()=>recoverCam();
 };
 for(const slot of [1,2]){
   const image=$('#multiPreview'+slot),cameraBox=image?.closest('.camera-preview');
   if(cameraBox){
     const pane=document.createElement('div');pane.id='kacaCameraControls'+slot;pane.className='kaca-camera-control-pane';
     pane.innerHTML='<p class="muted">Kontrol muncul setelah perangkat kamera aktif.</p>';
     cameraBox.appendChild(pane);
   }
 }
 const autoOpenCameraSettings=async()=>{
   await previewCameraAutomatically();
   if(window.kacaCurrentMenu!=='generalSettings')return;
   await Promise.all([loadCameraCapabilities(1),loadCameraCapabilities(2)]);
 };
 // Show orientation, flips and display quality immediately in the existing previews.
 const updatePreviewVisuals=()=>{
   const brightness=Number($('#livePreviewBrightness')?.value||100);
   for(const slot of [1,2]){
     const image=$('#multiPreview'+slot),stage=image?.closest('.kaca-camera-image-stage');
     if(!image||!stage)continue;
     const rotation=Number($('#cameraRotation'+slot)?.value||0);
     const flipX=$('#cameraFlipHorizontal'+slot)?.checked?-1:1,
           flipY=$('#cameraFlipVertical'+slot)?.checked?-1:1;
     const quarterTurn=rotation===90||rotation===270;
     // For quarter-turns swap the unrotated element dimensions. After rotation
     // its visible bounds exactly fit the clipping stage (no overflow).
     const width=stage.clientWidth||420,height=stage.clientHeight||260;
     image.style.width=quarterTurn?height+'px':'100%';
     image.style.height=quarterTurn?width+'px':'100%';
     image.style.position='absolute';image.style.left='50%';image.style.top='50%';
     image.style.transformOrigin='center center';
     image.style.transform=`translate(-50%, -50%) rotate(${rotation}deg) scaleX(${flipX}) scaleY(${flipY})`;
     image.style.filter=`brightness(${brightness}%)`;
   }
   const label=$('#livePreviewBrightnessValue');if(label)label.textContent=brightness+'%';
 };
 const previewResizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(updatePreviewVisuals):null;
 if(previewResizeObserver)for(const slot of [1,2]){
   const stage=$('#multiPreview'+slot)?.closest('.kaca-camera-image-stage');if(stage)previewResizeObserver.observe(stage);
 }
 for(const slot of [1,2])for(const part of ['cameraRotation','cameraFlipHorizontal','cameraFlipVertical']){
   $('#'+part+slot)?.addEventListener('input',updatePreviewVisuals);
 }
 $('#livePreviewBrightness')?.addEventListener('input',updatePreviewVisuals);
 for(const id of ['livePreviewQuality','livePreviewFps']){
   const item=$('#'+id);if(item)item.addEventListener('change',()=>{
     const q=Number($('#livePreviewQuality')?.value||76),fps=Number($('#livePreviewFps')?.value||15);
     for(const slot of [1,2]){
       const image=$('#multiPreview'+slot);
       if(image?.getAttribute('src')?.includes('/api/stream'))
         image.src=`http://127.0.0.1:8765/${slot===1?'api/stream.mjpg':'api/stream-secondary.mjpg'}?preview=${Date.now()}&quality=${q}&fps=${fps}`;
     }
   });
 }
 updatePreviewVisuals();
 mountGeneralSettingsSubmenus(autoOpenCameraSettings);

}

async function renderDevices(){
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / PYTHON CAMERA ENGINE</div><h3>Perangkat Kamera</h3><p style="color:#999;font-size:11px">Daftar perangkat menggabungkan webcam OpenCV/DirectShow dan Canon EDSDK. Pilih Canon untuk membuka Live View langsung melalui EDSDK; shutter jarak jauh tersedia saat sesi pemotretan.</p><div class="actions"><button class="btn" id="scan">Deteksi Semua Kamera</button><button class="btn secondary" id="detectCanon">Deteksi Canon EDSDK</button><button class="btn secondary" id="open">Aktifkan Preview</button><button class="btn secondary" id="canonShutter">Uji Shutter Canon</button><button class="btn secondary" id="snapshot">Uji 1 Frame</button><button class="btn secondary" id="jpegCheck">Periksa JPEG</button><button class="btn secondary" id="videoTest">Uji Rekam Video (5 detik)</button><button class="btn secondary" id="close">Matikan Kamera</button></div><div class="field" style="max-width:520px;margin-top:18px"><label>Daftar Perangkat Kamera</label><select id="cameras"><option value="">Tekan Deteksi Semua Kamera</option></select><small class="field-help">Pilih Canon EOS 1300D lalu tekan Aktifkan Preview. Live View menggunakan koneksi EDSDK terpisah dari OpenCV.</small></div><div id="canonStatus" class="notice" style="margin-top:8px">Status Canon EDSDK belum diperiksa.</div><div id="camStatus" class="notice">Memeriksa koneksi backend kamera lokal…</div><div id="frameStatus" class="notice" style="margin-top:8px">Belum ada frame yang diterima.</div><video id="videoTestPreview" controls playsinline style="display:none;width:100%;max-height:300px;margin-top:10px;background:#050506;border-radius:10px"></video><div class="camera-preview"><img id="cameraStream" alt="Preview kamera KACA.ID" style="width:100%;max-height:440px;object-fit:contain;display:none"><div id="previewEmpty" style="color:#777;font-size:12px;padding:35px">Preview kamera belum aktif</div></div><div class="panel" style="margin-top:10px"><div style="font-size:11px;color:#aaa;margin-bottom:6px">HASIL UJI SNAPSHOT (terpisah dari live preview)</div><img id="snapshotResult" alt="Hasil uji snapshot" style="display:none;max-width:100%;max-height:260px;object-fit:contain;background:#050506"><div id="snapshotInfo" style="font-size:11px;color:#aaa">Belum ada snapshot.</div></div><details style="margin-top:14px;color:#aaa" open><summary>Log diagnostik</summary><pre id="camLog" style="white-space:pre-wrap;max-height:260px;overflow:auto;font-size:11px"></pre></details></div><div class="panel"><h3>Informasi Engine</h3><div class="notice">Jika lampu kamera hanya berkedip saat deteksi, itu adalah tes singkat pembukaan perangkat. Saat preview aktif, status frame harus terus bertambah dan lampu kamera biasanya tetap menyala.</div></div>`;
 const status=$('#camStatus'), frameStatus=$('#frameStatus'), list=$('#cameras'), logEl=$('#camLog'), img=$('#cameraStream'), empty=$('#previewEmpty'), snapImg=$('#snapshotResult'), snapInfo=$('#snapshotInfo');let scanPoll=null, monitor=null, lastFrames=-1;
 const log=(m)=>{const line=new Date().toLocaleTimeString()+' '+m;logEl.textContent+=line+'\n';logEl.scrollTop=logEl.scrollHeight;};
 const stopMonitor=()=>{if(monitor){clearInterval(monitor);monitor=null;}};
 img.onload=()=>{empty.style.display='none';img.style.display='block';log('Elemen preview menerima gambar.');};
 img.onerror=()=>{frameStatus.textContent='Gambar preview gagal dimuat dari backend. Periksa status frame dan endpoint stream.';log('IMG ERROR: browser gagal memuat stream MJPEG.');};
 try{const h=await api('/health');status.textContent=`Backend aktif. OpenCV ${h.opencv||'belum terdeteksi'}. Tekan Deteksi Webcam.`;log('Backend terhubung; OpenCV '+h.opencv);}
 catch(e){status.textContent='Backend kamera belum aktif: '+e.message+'. Jalankan setup.bat lalu run-kaca-id.bat.';log('Koneksi backend gagal: '+e.message);}
 $('#scan').onclick=async()=>{stopMonitor();list.innerHTML='<option value="">Memindai kamera…</option>';status.textContent='Memindai perangkat. Lampu kamera dapat berkedip sebentar selama tes ini.';frameStatus.textContent='Pemindaian belum menguji preview kontinu.';log('Memulai pemindaian kamera backend');try{await api('/api/cameras?refresh=1');if(scanPoll)clearInterval(scanPoll);let ticks=0;scanPoll=setInterval(async()=>{ticks++;try{const s=await api('/api/status');if(s.scan_done){clearInterval(scanPoll);scanPoll=null;const webcamOptions=s.cameras.map(c=>`<option value="${c.id}">${c.label} · Webcam</option>`).join('');list.innerHTML=webcamOptions||'<option value="">Webcam tidak ditemukan</option>';let canonCount=0;try{const cr=await api('/api/canon/detect');const canonList=cr.cameras||[];canonCount=canonList.length;canonList.forEach(c=>{const opt=document.createElement('option');opt.value=c.id;opt.disabled=false;opt.textContent=`${c.name||'Canon EOS'} · Canon EDSDK / Live View`;list.appendChild(opt);});$('#canonStatus').textContent=(cr.sdk_available?'[EDSDK] ':'[USB/PnP] ')+cr.message+(canonCount?' | Terdaftar: '+canonList.map(c=>c.name).join(', ')+'. Pilih perangkat Canon lalu tekan Aktifkan Preview.':'');log('Canon inventory: '+(canonCount?canonList.map(c=>c.name).join(', '):cr.message));}catch(ce){$('#canonStatus').textContent='Pemeriksaan Canon gagal: '+ce.message;log('Canon detect error: '+ce.message);}if(s.cameras.length){const preferred=s.cameras.some(c=>c.id===Number(settings.cameraDevice))?Number(settings.cameraDevice):(s.cameras.some(c=>c.id===1)?1:s.cameras[0].id);list.value=String(preferred);settings.cameraDevice=preferred;await saveScopedSettings();status.textContent=`Webcam: ${s.cameras.length} perangkat. Canon EDSDK: ${canonCount} perangkat. Kamera ${preferred} dipilih sebagai default webcam.`;log('Webcam ditemukan: '+s.cameras.map(c=>c.label).join(', '));log('Kamera default dipilih: index '+preferred);}else{status.textContent='Pemindaian webcam selesai, tetapi webcam tidak ditemukan. '+(s.error||'')+(canonCount?' Canon terdeteksi. Pilih perangkat Canon pada daftar untuk mencoba Live View.':'');log('Tidak ada webcam: '+(s.error||''));}}else if(ticks>=180){clearInterval(scanPoll);scanPoll=null;status.textContent='Pemindaian webcam belum selesai dalam 90 detik. Status backend: '+(s.scan_stage||'tidak diketahui')+'. Periksa log backend.';log('Timeout polling scan; stage='+(s.scan_stage||'unknown'));}else if(ticks%6===0){status.textContent='Memindai webcam… '+(s.scan_stage||'menunggu backend');}}catch(e){clearInterval(scanPoll);scanPoll=null;status.textContent='Gagal membaca status pemindaian: '+e.message;log('Polling gagal: '+e.message);}},500);}catch(e){status.textContent='Gagal memulai pemindaian: '+e.message;log('Scan error: '+e.message);}};
 $('#detectCanon').onclick=async()=>{const b=$('#detectCanon'),out=$('#canonStatus');b.disabled=true;out.textContent='Menginisialisasi Canon EDSDK…';try{const r=await api('/api/canon/detect');const cams=r.cameras||[];const existing=[...list.options].filter(o=>String(o.value).startsWith('canon_edsdk_')).map(o=>o.value);existing.forEach(v=>{const o=[...list.options].find(x=>x.value===v);if(o)o.remove();});cams.forEach(c=>{const o=document.createElement('option');o.value=c.id;o.disabled=false;o.textContent=`${c.name||'Canon EOS'} · Canon EDSDK / Live View`;list.appendChild(o);});out.textContent=(r.sdk_available?'[EDSDK] ':'[USB/PnP] ')+r.message+(cams.length?' | '+cams.map(c=>c.name).join(', ')+' siap dicoba untuk Live View.':'');log('Canon EDSDK: '+r.message);}catch(e){out.textContent='Deteksi Canon gagal: '+e.message;log('Canon detect error: '+e.message);}finally{b.disabled=false;}};
 $('#open').onclick=async()=>{const selected=list.value;if(selected===''){status.textContent='Pilih kamera terlebih dahulu. Tekan Deteksi Semua Kamera jika daftar kosong.';return;}stopMonitor();status.textContent='Membuka kamera dan menunggu frame kontinu…';frameStatus.textContent='Menunggu frame pertama…';log('Membuka perangkat '+selected);try{let s;if(String(selected).startsWith('canon_edsdk_')){s=await api('/api/canon/open',{method:'POST',body:JSON.stringify({id:selected})});settings.cameraDeviceId=String(selected);settings.cameraDevice=Number(settings.cameraDevice??1);await saveScopedSettings();log('Canon Live View terbuka melalui EDSDK: '+s.name);}else{s=await api('/api/camera/open',{method:'POST',body:JSON.stringify({index:Number(selected)})});settings.cameraDevice=Number(selected);settings.cameraDeviceId=String(selected);await saveScopedSettings();log(`Open webcam berhasil: ${s.backend}; frame awal ${s.frame_width}x${s.frame_height}`);}img.style.display='block';empty.style.display='none';img.src='http://127.0.0.1:8765/api/stream.mjpg?ts='+Date.now();status.textContent=`Perangkat berhasil dibuka melalui ${s.backend||'Canon EDSDK Live View'}. Memeriksa apakah frame terus mengalir…`;lastFrames=s.frames||s.frames_read||0;let checks=0;monitor=setInterval(async()=>{checks++;try{const st=await api('/api/status');const age=st.last_frame_age_ms;frameStatus.textContent=`Frame: ${st.frames_read} | Resolusi: ${st.frame_width||0}×${st.frame_height||0} | Usia: ${age===null?'—':age+' ms'} | Reader: ${st.reader_alive?'aktif':'berhenti'} | Terang rata-rata: ${st.frame_mean??'—'}/255 (min ${st.frame_min??'—'}, maks ${st.frame_max??'—'})`;if(st.frames_read>lastFrames){if(checks===1||st.frames_read%30===0)log('Frame bertambah: '+st.frames_read+' ('+st.frame_width+'x'+st.frame_height+')');lastFrames=st.frames_read;}const cd=st.canon_diagnostics;if(cd&&checks%3===0){const n=cd.native||{};log('CANON DIAG: worker='+cd.worker_alive+', frameReader='+cd.frame_reader_alive+', statusReader='+cd.status_reader_alive+', exitcode='+cd.worker_exitcode+', exitReason='+(cd.worker_exit_info?.reason||cd.worker_exit_reason||cd.worker_exit_info?.detail||'—')+', threadException='+(cd.worker_exit_info?.thread_exception||n.thread_exception||n.startup_error||'—')+', heartbeatAge='+cd.worker_heartbeat_age_ms+'ms, nativeStage='+n.last_stage+', nativeFrames='+n.frames+', downloads='+n.download_attempts+', pending='+n.download_call_pending+', pendingSec='+n.download_call_elapsed+', code='+n.last_download_code+', streamBytes='+n.last_stream_length+', downloadErrors='+JSON.stringify(n.download_error_counts||{})+', eventErrors='+JSON.stringify(n.event_error_counts||{})+(cd.last_error?' workerError='+cd.last_error:'')+(cd.worker_traceback?' workerTraceback='+String(cd.worker_traceback).slice(-1800):'')+(n.diagnostic_error?' diagnosticError='+n.diagnostic_error:''));}if(!st.reader_alive||age===null||age>2500){status.textContent='Kamera terbuka, tetapi frame tidak mengalir stabil. '+(st.last_read_error||'Tidak ada frame baru dalam 2,5 detik.');if(checks===1||checks%3===0)log('PERINGATAN frame: reader='+st.reader_alive+', age='+age+', error='+st.last_read_error);}else{status.textContent='Preview aktif dan frame terus diterima.';}if(checks>=60){stopMonitor();log('Pemantauan otomatis selesai (60 pemeriksaan).');}}catch(e){frameStatus.textContent='Gagal membaca status frame: '+e.message;log('Status monitor error: '+e.message);}},1000);}catch(e){status.textContent='Kamera gagal dibuka: '+e.message;log('Open gagal: '+e.message);}};
 $('#canonShutter').onclick=async()=>{const b=$('#canonShutter');b.disabled=true;try{const r=await api('/api/canon/capture',{method:'POST',body:'{}'});status.textContent='Perintah shutter diterima oleh '+(r.device||'Canon')+'. '+(r.note||'');log('Uji shutter EDSDK berhasil dikirim.');}catch(e){status.textContent='Uji shutter Canon gagal: '+e.message;log('Uji shutter Canon gagal: '+e.message);}finally{b.disabled=false;}};
 $('#jpegCheck').onclick=async()=>{try{snapInfo.textContent='Memeriksa encoder JPEG di backend…';const d=await api('/api/jpeg-check');snapInfo.textContent=`Backend JPEG: ${d.jpeg_bytes} byte | header ${d.jpeg_magic_hex} | akhir ${d.jpeg_end_hex} | decode backend: ${d.backend_decode_ok?'BERHASIL':'GAGAL'} | ukuran ${d.decoded_shape||'—'}`;log('JPEG backend: '+JSON.stringify(d));}catch(e){snapInfo.textContent='Pemeriksaan JPEG gagal: '+e.message;log('JPEG CHECK ERROR: '+e.message);}};
 $('#snapshot').onclick=async()=>{try{snapInfo.textContent='Memuat snapshot langsung dari endpoint JPEG…';snapImg.onload=()=>{snapImg.style.display='block';snapInfo.textContent=`JPEG tampil: ${snapImg.naturalWidth}×${snapImg.naturalHeight}.`;log('Snapshot berhasil didekode browser: '+snapImg.naturalWidth+'x'+snapImg.naturalHeight);};snapImg.onerror=async()=>{let extra='';try{const d=await api('/api/jpeg-check');extra=' Backend decode='+d.backend_decode_ok+', magic='+d.jpeg_magic_hex+', bytes='+d.jpeg_bytes;}catch(e){extra=' Pemeriksaan backend gagal: '+e.message;}snapInfo.textContent='Browser gagal mendekode JPEG.'+extra;log('Browser JPEG decode gagal.'+extra);};snapImg.style.display='block';snapImg.src='http://127.0.0.1:8765/api/snapshot.jpg?ts='+Date.now();status.textContent='Snapshot diuji langsung dari endpoint. Live preview tidak diubah.';}catch(e){snapInfo.textContent='Uji snapshot gagal: '+e.message;status.textContent='Uji frame gagal: '+e.message;log('Snapshot gagal: '+e.message);}};
 $('#videoTest').onclick=async()=>{const b=$('#videoTest');b.disabled=true;try{status.textContent='Menyiapkan encoder dan memulai uji rekam video…';const started=await api('/api/video-test/start',{method:'POST',body:'{}'});log(`Uji video dimulai: ${started.width}×${started.height} @ ${started.fps} FPS, codec ${started.codec}.`);status.textContent='Merekam uji video selama 5 detik. Jangan matikan kamera…';await new Promise(resolve=>setTimeout(resolve,5000));const result=await api('/api/video-test/stop',{method:'POST',body:'{}'});status.textContent=`UJI VIDEO BERHASIL · ${result.width}×${result.height} · ${result.fps} FPS · ${result.frames} frame · ${result.duration_seconds} detik · ${(result.size_bytes/1024/1024).toFixed(2)} MB.`;frameStatus.textContent='Encoder berhasil merekam video langsung dari frame kamera.';const testVideo=$('#videoTestPreview');testVideo.src='http://127.0.0.1:8765/api/video-test.mp4?v='+Date.now();testVideo.style.display='block';log(status.textContent);}catch(e){status.textContent='UJI VIDEO GAGAL: '+e.message;log('Video test error: '+e.message);}finally{b.disabled=false;}};
 $('#close').onclick=async()=>{stopMonitor();try{await api('/api/camera/close',{method:'POST',body:'{}'});}catch(e){}img.removeAttribute('src');img.style.display='none';empty.style.display='block';status.textContent='Kamera dihentikan.';frameStatus.textContent='Tidak ada frame aktif.';log('Kamera ditutup');};
}

async function renderSessionSettings(){
 const mode=settings.sessionMode||'fixed_count';const hasManualLayout=Array.isArray(settings.layoutSlots)&&settings.layoutSlots.length>0;const slots=hasManualLayout?settings.layoutSlots.length:Number(settings.frameSlots||4);const captureCount=hasManualLayout?Math.max(1,Math.max(...settings.layoutSlots.map((v,i)=>Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i))+1):slots;const duration=Number(settings.sessionDurationMinutes||5);
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / SESSION CONFIGURATION</div><h3>Pengaturan Mode Sesi Foto</h3><p class="muted">Pilih salah satu mode untuk menentukan kesempatan customer. Mode ini berlaku untuk sesi baru.</p><div class="mode-cards"><label class="mode-card ${mode==='fixed_count'?'selected':''}"><input type="radio" name="sessionMode" value="fixed_count" ${mode==='fixed_count'?'checked':''}><div><b>Mode 1 · Berdasarkan jumlah foto pada frame</b><p>Jumlah kesempatan foto mengikuti jumlah foto sumber yang unik pada frame. Slot duplikat dapat menampilkan foto yang sama lebih dari sekali tanpa menambah kesempatan pemotretan.</p><small>Contoh: 4 slot dengan sumber Foto 1, Foto 1, Foto 2, Foto 3 = 3 kesempatan foto.</small></div></label><label class="mode-card ${mode==='timed'?'selected':''}"><input type="radio" name="sessionMode" value="timed" ${mode==='timed'?'checked':''}><div><b>Mode 2 · Berdasarkan durasi sesi</b><p>Customer bebas mengambil foto selama waktu masih tersedia. Setelah waktu habis, customer memilih foto terbaik untuk dimasukkan ke slot frame.</p><small>Contoh: 5 menit bebas foto, lalu pilih maksimal sesuai slot layout.</small></div></label></div><div class="form-grid session-setting-fields"><div class="field"><label>Jumlah slot frame / layout</label><select id="settingFrameSlots" ${hasManualLayout?'disabled':''}>${[1,2,3,4,5,6,7,8].map(n=>`<option value="${n}" ${slots===n?'selected':''}>${n} foto</option>`).join('')}</select><small class="field-help">${hasManualLayout?'Jumlah visual dikunci mengikuti '+slots+' slot layout manual ('+captureCount+' foto sumber unik). Atur slot dan foto sumbernya melalui menu Frame & Layout.':'Mode 1 memakai jumlah foto sumber unik. Slot duplikat tidak menambah kesempatan.'}</small></div><div class="field" id="durationField"><label>Durasi sesi foto (menit)</label><input id="settingDuration" type="number" min="1" max="60" value="${duration}"><small class="field-help">Mode 2: waktu dihitung sejak customer menekan Mulai Sesi.</small></div><div class="field"><label>Jeda setelah jumlah foto terpenuhi (detik)</label><input id="completionDelaySeconds" type="number" min="0" max="60" value="${settings.completionDelaySeconds??10}"><small class="field-help">Setelah foto terakhir diambil, customer diberi waktu sebelum otomatis berpindah ke slide filter/hasil. Isi 0 untuk langsung lanjut.</small></div><div class="field"><label>Timer otomatis slide hasil (detik)</label><input id="resultReturnSeconds" type="number" min="5" max="600" value="${settings.resultReturnSeconds||30}"><small class="field-help">Setelah waktu habis, aplikasi kembali ke Preview Kamera.</small></div></div><div class="notice" id="sessionSettingsNotice">Mode aktif: ${mode==='timed'?'Berdasarkan durasi':'Berdasarkan jumlah slot frame'}.</div><div class="actions"><button class="btn" id="saveSessionSettings">Simpan Pengaturan Sesi</button></div></div><div class="panel"><div class="eyebrow2">LIVE PHOTO</div><h3>Rekaman Video per Foto</h3><p class="muted">Saat customer menekan Ambil Foto, kamera langsung merekam selama durasi yang dipilih. Hitung mundur capture mengikuti durasi tersebut. Ketika hitung mundur mencapai nol, rekaman berhenti dan kamera langsung mengambil foto.</p><label class="mode-card" style="display:flex;align-items:center;gap:14px;margin-top:14px"><input id="livePhotoToggle" type="checkbox" ${settings.livePhotoEnabled?'checked':''} style="width:18px;height:18px"><span><b>Aktifkan Live Photo</b><small>Setiap foto menghasilkan satu video MP4 tersendiri.</small></span></label><div class="field" style="margin-top:14px"><label>Durasi Live Photo / Countdown Capture</label><select id="livePhotoDuration">${[5,10,15,20,25,30].map(n=>`<option value="${n}" ${Number(settings.livePhotoDuration||5)===n?'selected':''}>${n} detik</option>`).join('')}</select><small class="field-help">Pilihan durasi 5 sampai 30 detik. Durasi ini otomatis menjadi hitung mundur saat Live Photo aktif.</small></div><div class="notice" style="margin-top:12px">Aplikasi akan memeriksa jumlah frame video sebelum menyatakan Live Photo berhasil.</div><div class="panel" style="margin-top:16px"><h3>Keamanan Sesi</h3><div class="field"><label>PIN untuk membuka kunci Keluar dari Sesi</label><input id="exitSessionPin" type="password" inputmode="numeric" maxlength="12" placeholder="Buat PIN operator" value="${String(settings.exitSessionPin||'').replaceAll('&','&amp;').replaceAll('\"','&quot;')}"><small class="field-help">PIN ini diminta setiap kali tombol Keluar dari Sesi ditekan. Simpan PIN di tempat aman.</small></div></div></div>`;
 document.querySelectorAll('input[name="sessionMode"]').forEach(r=>r.onchange=()=>{document.querySelectorAll('.mode-card').forEach(c=>c.classList.toggle('selected',c.querySelector('input').checked));$('#durationField').style.opacity=$('input[name="sessionMode"]:checked').value==='timed'?'1':'.45';});
 $('#durationField').style.opacity=mode==='timed'?'1':'.45';
 $('#saveSessionSettings').insertAdjacentHTML('beforebegin',`<div class="panel kaca-session-print-options"><h3>Opsi Tambah Cetak & Cetak Otomatis</h3><p class="muted">Tentukan apakah pelanggan boleh memilih tambahan salinan pada slide Hasil. Cetak otomatis mengunci tombol cetak untuk menghindari pengulangan tanpa sengaja.</p><label class="frame-enable-check"><input id="additionalPrintEnabled" type="checkbox" ${settings.additionalPrintEnabled?'checked':''}><span>Aktifkan tombol Tambah Cetak di hasil akhir</span></label><div class="field"><label>Maksimum jumlah salinan yang dapat dipilih pelanggan</label><select id="additionalPrintMaxCopies">${[1,2,3,4,5,6,7,8,9,10,15,20].map(n=>`<option value="${n}" ${Number(settings.additionalPrintMaxCopies||5)===n?'selected':''}>${n} lembar</option>`).join('')}</select></div><label class="frame-enable-check"><input id="autoPrintEnabled" type="checkbox" ${settings.autoPrintEnabled?'checked':''}><span>Cetak otomatis saat slide Hasil Akhir tampil</span></label><p class="muted">Pada cetak otomatis, file dengan QR (jika diaktifkan) akan disiapkan dahulu. Tombol Cetak Hasil akan terkunci. Pastikan printer dipilih pada menu Printer & Kertas.</p></div>`);
 $('#autoPrintEnabled').onchange=()=>{if($('#autoPrintEnabled').checked){$('#additionalPrintEnabled').checked=false;$('#additionalPrintEnabled').disabled=true;}else $('#additionalPrintEnabled').disabled=false;};
 $('#autoPrintEnabled').onchange();
 $('#saveSessionSettings').onclick=async()=>{settings.sessionMode=$('input[name="sessionMode"]:checked').value;settings.frameSlots=String(hasManualLayout?settings.layoutSlots.length:$('#settingFrameSlots').value);settings.sessionDurationMinutes=Math.max(1,Math.min(60,Number($('#settingDuration').value)||5));settings.resultReturnSeconds=Math.max(5,Math.min(600,Number($('#resultReturnSeconds').value)||30));settings.completionDelaySeconds=Math.max(0,Math.min(60,Number($('#completionDelaySeconds').value)||0));settings.livePhotoEnabled=$('#livePhotoToggle').checked;settings.livePhotoDuration=Math.max(5,Math.min(30,Number($('#livePhotoDuration').value)||5));settings.exitSessionPin=$('#exitSessionPin').value.trim();settings.additionalPrintEnabled=$('#additionalPrintEnabled').checked;settings.additionalPrintMaxCopies=Math.max(1,Math.min(20,Number($('#additionalPrintMaxCopies').value)||5));settings.autoPrintEnabled=$('#autoPrintEnabled').checked;await saveScopedSettings();$('#sessionSettingsNotice').textContent=`Tersimpan. Mode ${settings.sessionMode==='timed'?'Durasi':'Jumlah Foto'}, ${settings.frameSlots} slot frame${settings.sessionMode==='timed'?' · '+settings.sessionDurationMinutes+' menit':''}. Live Photo ${settings.livePhotoEnabled?'aktif · '+settings.livePhotoDuration+' detik':'nonaktif'}.`;};
}

async function renderVideoCapture(){
 const root=$('#content');
 root.className='photo-session-content video-session-content';
 root.dataset.flowStep='0';
 const duration=Math.max(5,Math.min(300,Number(settings.videoDurationSeconds)||30));
 root.innerHTML=`<div class="photo-flow-head"><div class="eyebrow2">KACA.ID / VIDEO SESSION</div><h2>Video Studio</h2><p>Rekam video, tinjau hasil, lalu bagikan dengan QR atau WhatsApp.</p><button class="btn secondary" id="flowExit">Keluar dari Sesi</button></div>
 <div class="photo-flow-steps">${[['Transaksi',1],['Rekam Video',3],['Preview',4],['Hasil',5]].map(([label,step],i)=>`<div data-step-label="${step}" class="flow-step"><b>0${i+1}</b><span>${label}</span></div>`).join('')}</div>
 <section class="transaction-method-panel" id="flowTransactionPanel" hidden><div class="transaction-method-title">PILIH METODE TRANSAKSI</div><div class="transaction-method-options"><button type="button" class="transaction-method-choice" data-transaction-method="voucher"><span class="transaction-voucher-mark">VOUCHER</span><b>Voucher</b></button><button type="button" class="transaction-method-choice" data-transaction-method="qris"><span class="transaction-qris-mark">QRIS</span><b>QRIS</b></button></div></section>
 <section class="flow-frame-panel" id="flowFramePanel" hidden><div class="flow-frame-heading"><div class="eyebrow2">KACA.ID / VIDEO FRAME</div><h3>Frame Video Otomatis</h3><p class="muted">Frame ditentukan oleh pengaturan admin/Event.</p></div><div class="flow-frame-layout"><div class="flow-frame-list-wrap"><div class="flow-frame-list-label">DAFTAR FRAME</div><div class="flow-frame-grid" id="flowFrameGrid"></div></div><div class="flow-frame-preview-wrap"><div class="flow-frame-preview-label">PREVIEW FRAME</div><div class="flow-frame-preview-stage"><img id="flowFramePreviewImage" alt="Frame video terpilih" hidden><span id="videoNoFrameInfo" class="empty">Tanpa Frame</span></div><div id="flowFrameNextMount"><button class="btn" id="videoFrameNext">LANJUT</button></div><p class="notice" id="flowFrameStatus">Pilih frame lalu lanjutkan.</p></div></div></section>
 <section class="capture-grid video-capture-grid" id="videoCaptureGrid" hidden><div class="panel"><div class="eyebrow2">KACA.ID / VIDEO CAPTURE</div><h3>Rekam Video</h3><div class="capture-preview video-record-preview" id="videoPreviewBox"><img id="videoLivePreview" alt="Preview kamera video"><div id="videoPreviewEmpty" class="empty">Menyiapkan kamera…</div><img id="videoFrameOverlay" class="video-frame-overlay" alt="Overlay frame video" hidden><div class="count-overlay" id="videoCountOverlay" hidden></div><button class="preview-icon-button preview-mirror-button" id="videoMirror" type="button" title="Balik preview"><img class="preview-icon-asset" src="assets/mirror-camera.svg" alt=""></button><div class="preview-bottom-controls"><button class="preview-tool-button" id="videoStart" type="button">MULAI REKAM</button></div></div><p class="notice" id="videoStatus">Kamera siap untuk merekam.</p></div><div class="panel video-capture-controls"><div class="session-photos-heading"><div><div class="eyebrow2">SESSION VIDEO</div><h3>Rekaman Video</h3></div><button type="button" class="btn secondary" id="videoExit">KELUAR</button></div><div class="progress-track"><div id="videoProgress"></div></div><div id="videoCountdown" class="shot-counter">${duration} detik</div><div class="video-control-row"><button id="videoStop" class="btn secondary" disabled>HENTIKAN & TINJAU HASIL</button></div><p class="muted">Video hasil rekaman langsung disimpan lokal. Upload Google Drive berjalan otomatis di latar belakang.</p></div></section>
 <section class="filter-review-panel video-review-panel" id="videoReviewPanel" hidden><div class="filter-review-head"><div class="eyebrow2">KACA.ID / VIDEO PREVIEW</div><h3>Periksa Rekaman Anda</h3><p>Putar preview lalu lanjut ke slide hasil untuk scan QR dan berbagi.</p></div><div class="video-review-stage"><video id="videoReviewPlayer" playsinline muted loop controls preload="metadata" aria-label="Preview rekaman"></video><div class="video-review-info" id="videoReviewInfo">Video tersimpan lokal.</div></div><div class="video-review-actions"><button class="btn secondary" id="videoRetake">↶ ULANGI VIDEO</button><button class="btn" id="videoContinue">LANJUT KE HASIL</button></div></section>
 <section class="video-final-panel" id="videoFinishedResult" hidden></section>
 <div class="flow-slide-loading" id="videoSlideLoading" hidden role="status" aria-live="polite"><div class="flow-slide-loading-spinner"></div><strong>Tunggu kakak...😊</strong><span id="videoLoadingText">Mempersiapkan frame dan kamera video…</span><button class="btn secondary" id="videoRetryFrames" hidden>Coba Muat Frame Lagi</button></div>`;
 let active=false,stopping=false,remaining=duration,ticker=null,videoId=null,videoUrl='',localPath='',driveShareUrl='',drivePolling=null,videoTimer=null,selectedTransactionMethod='',redeemedVoucherCode='',paidQrisInvoice='',captureUiReady=true;
 const $v=id=>root.querySelector(id);
 const status=$v('#videoStatus'),transactionPanel=$v('#flowTransactionPanel'),loading=$v('#videoSlideLoading');
 const preview=$v('#videoLivePreview'),empty=$v('#videoPreviewEmpty'),start=$v('#videoStart'),stop=$v('#videoStop'),count=$v('#videoCountdown');
 const videoAngle=settings.multicamEnabled&&Number(settings.activeCameraAngle||0)===1?1:0;
 const setStage=(stage)=>{if(stage===2)stage=3;root.dataset.flowStep=String(stage);for(const [id,n] of [['flowTransactionPanel',1],['flowFramePanel',2],['videoCaptureGrid',3],['videoReviewPanel',4],['videoFinishedResult',5]]){const el=$v('#'+id);if(el)el.hidden=n!==stage;}root.querySelectorAll('[data-step-label]').forEach(el=>{const n=Number(el.dataset.stepLabel);el.classList.toggle('active',n===stage);el.classList.toggle('done',n<stage);});};
 const showLoading=text=>{loading.hidden=false;$v('#videoLoadingText').textContent=text;};const hideLoading=()=>{loading.hidden=true;};
 let mirrorVideo=!!settings.mirrorPreview;
 const applyVideoAngleOrientation=()=>{
  const suffix=videoAngle===1?'2':'',rot=Number(settings['cameraRotation'+suffix]||0);
  const flipX=!!settings['cameraFlipHorizontal'+suffix],flipY=!!settings['cameraFlipVertical'+suffix];
  preview.style.transform=`scaleX(${(flipX?-1:1)*(mirrorVideo?-1:1)}) scaleY(${flipY?-1:1}) rotate(${rot}deg)`;
  preview.style.objectFit='contain';
  const stage=$v('#videoPreviewBox'),width=stage?.clientWidth||640,height=stage?.clientHeight||400;
  // Keep portrait orientation inside the original video preview box.
  if(rot===90||rot===270){const ratio=Math.min(1,width/Math.max(1,height),height/Math.max(1,width));preview.style.maxWidth=(height*ratio)+'px';preview.style.maxHeight=(width*ratio)+'px';}
  else{preview.style.maxWidth='100%';preview.style.maxHeight='100%';}
 };
 $v('#videoMirror').onclick=()=>{mirrorVideo=!mirrorVideo;applyVideoAngleOrientation();$v('#videoMirror').setAttribute('aria-pressed',String(mirrorVideo));};
 applyVideoAngleOrientation();
 const stopTicker=()=>{if(ticker){clearInterval(ticker);ticker=null;}};
 const stopPolling=()=>{if(drivePolling){clearInterval(drivePolling);drivePolling=null;}if(videoTimer){clearInterval(videoTimer);videoTimer=null;}};
 const openCamera=async()=>{if(videoAngle===1){const id=String(settings.multicamCamera2??'');if(!id)throw new Error('Angle 2 belum dipilih pada Pengaturan Umum.');if(id.startsWith('canon_edsdk_'))await api('/api/camera/secondary/canon/open',{method:'POST',body:JSON.stringify({id})});else await api('/api/camera/secondary/open',{method:'POST',body:JSON.stringify({index:Number(id)})});}else{let st=await api('/api/status');if(!st.camera_open){const saved=String(settings.cameraDeviceId||'');if(saved.startsWith('canon_edsdk_'))await api('/api/canon/open',{method:'POST',body:JSON.stringify({id:saved})});else await api('/api/camera/open',{method:'POST',body:JSON.stringify({index:Number(settings.cameraDevice??1)})});}}preview.onload=()=>{empty.hidden=true;};preview.onerror=()=>{empty.hidden=false;empty.textContent='Kamera belum tersedia. Periksa Pengaturan Perangkat.';};preview.src=`http://127.0.0.1:8765/${videoAngle===1?'api/stream-secondary.mjpg':'api/stream.mjpg'}?videomode=${Date.now()}`;};
 let chosenFrameId='',videoPaymentApproved=false;const frameGrid=$v('#flowFrameGrid');
 const showVideoFrameStep=async()=>{
   videoPaymentApproved=true;
   showLoading('Menyiapkan kamera video dengan frame dari Pengaturan/Event…');
   try{await openCamera();if(root!==$('#content'))return;setStage(3);hideLoading();status.textContent='Kamera siap. Tekan MULAI REKAM.';}
   catch(e){showLoading('Kamera belum siap: '+e.message);$v('#videoRetryFrames').hidden=false;$v('#videoRetryFrames').textContent='Coba Hubungkan Kamera';}
 };
 transactionPanel.querySelectorAll('[data-transaction-method]').forEach(btn=>btn.onclick=async()=>{if(!captureUiReady){status.textContent='Menyiapkan kamera dan sesi. Tunggu sebentar lalu coba kembali.';return;}const method=btn.dataset.transactionMethod;try{if(method==='voucher'){const code=await requestVoucherCode();if(code===null)return;const result=await api('/api/vouchers/validate',{method:'POST',body:JSON.stringify({code})});if(!result.ok)throw new Error(result.error||'Voucher tidak valid.');redeemedVoucherCode=result.voucher.code;selectedTransactionMethod='voucher';alert('Voucher valid. Sisa penggunaan setelah sesi dimulai: '+result.remaining_uses+'.');}else{const q=await api('/api/qris/status');if(!q.configured)throw new Error('QRIS belum dikonfigurasi admin. Buka menu Pembayaran.');
 if(q.mode==='doku_checkout'){
   const checkout=await api('/api/qris/checkout/create',{method:'POST',body:'{}'});
   const gate=document.createElement('div');gate.className='session-pin-overlay';
   gate.innerHTML=`<div class="session-pin-card qris-online-card"><h3>Bayar QRIS — Rp ${Number(checkout.amount).toLocaleString('id-ID')}</h3><p>Scan QRIS pada halaman DOKU berikut. Setelah pembayaran berhasil dikonfirmasi DOKU, aplikasi akan otomatis lanjut.</p><iframe id="dokuCheckoutFrame" title="Pembayaran QRIS DOKU" src="${esc(checkout.checkout_url)}" loading="eager" referrerpolicy="no-referrer" sandbox="allow-scripts allow-forms allow-same-origin allow-popups"></iframe><p id="dokuCheckoutProgress" class="notice">Menunggu pembayaran. Pemeriksaan transaksi mulai setelah 60 detik sesuai rekomendasi DOKU.</p><div class="actions"><button type="button" class="btn secondary" data-doku-open>Tampilkan QRIS di KACA.ID</button><button type="button" class="btn secondary" data-doku-cancel>Batalkan</button></div></div>`;
   document.body.appendChild(gate);
   let polling=false,closed=false;
   const clean=()=>{closed=true;clearInterval(timer);window.kaca.closeQrisCheckout?.().catch(()=>{});gate.remove();};
   gate.querySelector('[data-doku-cancel]').onclick=clean;
   gate.querySelector('[data-doku-open]').onclick=()=>window.kaca.openQrisCheckout(checkout.checkout_url).catch(e=>{gate.querySelector('#dokuCheckoutProgress').textContent='Gagal membuka Checkout DOKU di KACA.ID: '+e.message;});
   const check=async()=>{if(closed||polling)return;polling=true;try{
     const st=await api('/api/qris/checkout/status?invoice='+encodeURIComponent(checkout.invoice));
     if(st.status==='paid'){
       clean();selectedTransactionMethod='qris_doku';paidQrisInvoice=checkout.invoice;redeemedVoucherCode='';
       transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));
       void showVideoFrameStep();
     } else if(['expired','failed'].includes(st.status)){
       gate.querySelector('#dokuCheckoutProgress').textContent='Pembayaran '+st.status+'. Batalkan lalu coba transaksi baru.';
       clearInterval(timer);
     } else {
       gate.querySelector('#dokuCheckoutProgress').textContent='Menunggu konfirmasi pembayaran dari DOKU… Invoice '+checkout.invoice;
     }
   }catch(e){gate.querySelector('#dokuCheckoutProgress').textContent='Pemeriksaan pembayaran: '+e.message;}finally{polling=false;}};
   const timer=setInterval(check,10000);void check();return;
 }
 const gate=document.createElement('div');gate.className='session-pin-overlay';gate.innerHTML=`<div class="session-pin-card qris-customer-card"><div class="eyebrow2">PEMBAYARAN QRIS</div><h3>${esc(q.merchant_name||'KACA.ID')}</h3><img src="http://127.0.0.1:8765/api/qris/image?v=${Date.now()}" alt="QRIS" style="display:block;max-width:260px;max-height:260px;object-fit:contain;background:white;padding:12px;margin:16px auto;border-radius:12px"><b>Rp ${Number(q.amount||settings.sessionPrice||0).toLocaleString('id-ID')}</b><p>${esc(q.instructions||'Scan QRIS dan tunjukkan bukti pembayaran kepada operator.')}</p><p class="field-help">Sesi hanya dapat dilanjutkan setelah operator memeriksa pembayaran.</p><input type="password" id="qrisOperatorPin" placeholder="PIN operator" inputmode="numeric"><div class="actions"><button type="button" class="btn secondary" data-qris-cancel>Batal</button><button type="button" class="btn" data-qris-approve>Operator: verifikasi & lanjut</button></div><small class="pin-error" id="qrisPinError"></small></div>`;document.body.appendChild(gate);gate.querySelector('[data-qris-cancel]').onclick=()=>gate.remove();gate.querySelector('[data-qris-approve]').onclick=()=>{if(gate.querySelector('#qrisOperatorPin').value!==String(settings.adminPin||'1234')){gate.querySelector('#qrisPinError').textContent='PIN operator salah.';return;}gate.remove();selectedTransactionMethod='qris_manual';redeemedVoucherCode='';transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));void showVideoFrameStep();};return;}transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));void showVideoFrameStep();}catch(e){alert(e.message);}});
 const buttonMap=transactionPanel.querySelectorAll('[data-transaction-method]');buttonMap.forEach(b=>{b.hidden=b.dataset.transactionMethod==='voucher'?settings.enableVoucherPayment===false:settings.enableQrisPayment===false;b.disabled=b.hidden;});
 const updatePreview=()=>{const img=$v('#flowFramePreviewImage');const title=$v('#videoNoFrameInfo');const overlay=$v('#videoFrameOverlay');if(chosenFrameId){const url=`http://127.0.0.1:8765/api/frames/${chosenFrameId}.png`;img.src=url;img.hidden=false;title.hidden=true;overlay.src=url;overlay.hidden=false;}else{img.hidden=true;img.removeAttribute('src');title.hidden=false;overlay.hidden=true;overlay.removeAttribute('src');}frameGrid.querySelectorAll('[data-frame-id]').forEach(el=>el.classList.toggle('chosen',el.dataset.frameId===chosenFrameId));};
 const prepareFrames=async()=>{showLoading('Memuat seluruh frame yang tersedia…');const r=await api('/api/frames');const frames=(r.frames||[]).filter(f=>f.enabled!==false&&f.active!==false&&frameBelongsToCurrentEvent(f));frameGrid.innerHTML=`<button class="flow-frame-choice" data-frame-id="" aria-label="Tanpa Frame"><div class="frame-choice-blank">–</div><b>Tanpa Frame</b></button>`+frames.map(f=>`<button class="flow-frame-choice" data-frame-id="${esc(f.id)}"><img src="http://127.0.0.1:8765/api/frames/${encodeURIComponent(f.id)}.png" alt="Frame ${esc(f.name)}"><b>${esc(f.name)}</b></button>`).join('');chosenFrameId=frames.some(f=>f.id===settings.frameId)?settings.frameId:'';/* Frame is selected in Frame & Layout/Event, not during customer flow. */updatePreview();await Promise.all(frames.filter(f=>f.id===chosenFrameId).map(f=>new Promise((resolve,reject)=>{const img=new Image(),timeout=setTimeout(()=>reject(new Error('Timeout frame '+f.name)),12000);img.onload=()=>{clearTimeout(timeout);if(typeof img.decode==='function')img.decode().then(resolve).catch(reject);else resolve();};img.onerror=()=>{clearTimeout(timeout);reject(new Error('Frame gagal '+f.name));};img.src=`http://127.0.0.1:8765/api/frames/${encodeURIComponent(f.id)}.png`; })));hideLoading();};
 $v('#videoRetryFrames').onclick=async()=>{try{await prepareFrames();if(root!==$('#content'))return;if(videoPaymentApproved||settings.enableVoucherPayment===false&&settings.enableQrisPayment===false)await showVideoFrameStep();else{setStage(1);hideLoading();}$v('#videoRetryFrames').hidden=loading.hidden;}catch(e){$v('#videoLoadingText').textContent=e.message;$v('#videoRetryFrames').hidden=false;}};
 $v('#videoFrameNext').onclick=async()=>{showLoading('Menyiapkan kamera dan preview video…');try{await openCamera();setStage(3);hideLoading();status.textContent='Kamera siap. Tekan MULAI REKAM.';}catch(e){hideLoading();$v('#flowFrameStatus').textContent='Gagal membuka kamera: '+e.message;}};
 const finishRecording=async()=>{if(!active||stopping)return;stopping=true;stopTicker();stop.disabled=true;start.disabled=true;showLoading('Menutup MP4 dan menyimpannya ke lokal…');try{const r=await api('/api/video/stop',{method:'POST',body:'{}'});if(!r.ok||!r.id)throw new Error(r.error||'File video belum tersedia.');active=false;$v('#videoMirror').disabled=false;videoId=r.id;videoUrl=r.url;localPath=r.local_path||'';const player=$v('#videoReviewPlayer');player.controls=true;player.muted=true;
  let previewReady=false,previewError='';
  for(let i=0;i<100;i++){
    if(root!==$('#content'))return;
    const st=await api(`/api/video/${encodeURIComponent(videoId)}/status`);
    if(st.preview_ready){videoUrl=st.preview_url;previewReady=true;break;}
    if(st.preview_error){previewError=st.preview_error;break;}
    $v('#videoLoadingText').textContent='Menyiapkan video WebM agar dapat diputar di slide hasil…';
    await new Promise(resolve=>setTimeout(resolve,500));
  }
  if(!previewReady)videoUrl=r.url;
  player.src=videoUrl;player.controls=true;player.muted=true;
  player.onerror=()=>{$v('#videoReviewInfo').textContent='Preview tidak kompatibel pada perangkat ini; MP4 asli tetap tersimpan dan bisa diunduh melalui slide hasil.';};
  player.play().catch(()=>{});
  $v('#videoReviewInfo').textContent=`${Number(r.duration_seconds||0).toFixed(1)} detik · ${(Number(r.size_bytes||0)/1048576).toFixed(1)} MB · ${r.frames||0} frame · ${r.local_path?'Tersimpan lokal':'Periksa arsip lokal'}${!previewReady?' · WebM belum siap: '+(previewError||'encoder lambat'):''}`;setStage(4);hideLoading();status.textContent='Video tersimpan; tinjau hasil lalu lanjutkan.';}catch(e){hideLoading();status.textContent='Gagal menyelesaikan video: '+e.message;start.disabled=false;}finally{stopping=false;}};
 start.onclick=async()=>{if(active||stopping)return;try{start.disabled=true;const r=await api('/api/video/start',{method:'POST',body:JSON.stringify({angle:videoAngle,event_id:activeEvent()?.id||null,event_name:activeEvent()?.name||'',frame_id:chosenFrameId,mirror:mirrorVideo,camera_rotation:Number(settings[videoAngle===1?'cameraRotation2':'cameraRotation']||0),camera_flip_horizontal:!!settings[videoAngle===1?'cameraFlipHorizontal2':'cameraFlipHorizontal'],camera_flip_vertical:!!settings[videoAngle===1?'cameraFlipVertical2':'cameraFlipVertical'],payment_method:selectedTransactionMethod,payment_invoice:paidQrisInvoice||null,voucher_code:redeemedVoucherCode||null})});if(!r.ok||!r.id)throw new Error(r.error||'Tidak dapat memulai rekaman.');videoId=r.id;active=true;
  // The payment/voucher is consumed exactly once per customer, not again on RETAKE.
  selectedTransactionMethod='';redeemedVoucherCode='';paidQrisInvoice='';
  $v('#videoMirror').disabled=true;
  remaining=duration;count.textContent=remaining+' detik tersisa';stop.disabled=false;status.textContent='Sedang merekam video…';$v('#videoProgress').style.width='0%';ticker=setInterval(()=>{remaining--;count.textContent=Math.max(0,remaining)+' detik tersisa';$v('#videoProgress').style.width=((duration-Math.max(0,remaining))/duration*100)+'%';if(remaining<=0)void finishRecording();},1000);}catch(e){status.textContent='Rekaman tidak bisa dimulai: '+e.message;start.disabled=false;}};
 stop.onclick=()=>void finishRecording();
 const retake=async()=>{if(active)return;stopPolling();try{$v('#videoReviewPlayer').pause();}catch{}videoId=null;videoUrl='';driveShareUrl='';stop.disabled=true;start.disabled=false;count.textContent=duration+' detik';$v('#videoProgress').style.width='0%';status.textContent='Siap merekam ulang.';setStage(3);};
 $v('#videoRetake').onclick=retake;
 $v('#videoContinue').onclick=async()=>{if(!videoId)return;showLoading('Menyiapkan preview video untuk hasil akhir…');const player=$v('#videoReviewPlayer');if(!player.videoWidth){await new Promise(resolve=>{const t=setTimeout(resolve,2800);player.addEventListener('loadeddata',()=>{clearTimeout(t);resolve();},{once:true});});}setStage(5);hideLoading();openVideoResult();};
 const leave=()=>{stopTicker();stopPolling();try{$v('#videoReviewPlayer')?.pause();$v('#videoResultPlayer')?.pause();}catch{}return go('dashboard');};
 const exit=()=>{const pin=String(settings.exitSessionPin||'').trim();if(!pin){status.textContent='Keluar dari sesi memerlukan PIN operator di Pengaturan Sesi.';return;}const gate=document.createElement('div');gate.className='session-pin-overlay';gate.innerHTML=`<form class="session-pin-card"><h3>Keluar dari Sesi Video</h3><p>Masukkan PIN operator.</p><input type="password" inputmode="numeric" required><div class="actions"><button class="btn secondary" type="button" data-cancel>Batal</button><button class="btn" type="submit">Buka Kunci</button></div><small class="pin-error"></small></form>`;document.body.appendChild(gate);gate.querySelector('[data-cancel]').onclick=()=>gate.remove();gate.querySelector('form').onsubmit=e=>{e.preventDefault();if(gate.querySelector('input').value!==pin){gate.querySelector('.pin-error').textContent='PIN salah.';return;}gate.remove();if(active){status.textContent='Selesaikan rekaman aktif sebelum keluar.';return;}leave();};};
 $v('#flowExit').onclick=exit;$v('#videoExit').onclick=exit;
 const openVideoResult=()=>{
   const destination=$v('#videoFinishedResult');const url=videoUrl,videoKey=videoId;
   destination.innerHTML=`<div class="result-card result-card-final"><div class="result-topline"><b>Hasil Video ${esc(videoKey)}</b><span>Rekaman MP4 · ${activeEvent()?esc(activeEvent().name):'Sesi Umum'}</span></div><div class="result-workspace result-workspace-final"><section class="result-preview-column result-preview-column-final"><div class="result-preview-stage result-preview-stage-split"><section class="result-media-pane result-photo-pane"><div class="result-media-pane-inner"><img id="videoResultPoster" src="http://127.0.0.1:8765/api/video/${videoKey}/poster.jpg" alt="Foto preview video"></div><div class="result-media-caption">PREVIEW VIDEO</div></section><section class="result-media-pane result-live-pane"><div class="result-media-pane-inner"><video id="videoResultPlayer" autoplay muted loop playsinline preload="auto" disablepictureinpicture disableremoteplayback aria-label="Video hasil rekaman"></video></div><div class="result-media-caption">HASIL REKAMAN VIDEO</div></section></div></section><section class="result-files-column result-files-column-final"><section class="drive-qr-card"><div class="drive-qr-copy"><b>SCAN QR CODE UNTUK HASIL DIGITAL</b><p id="videoDriveStatus">Menyiapkan folder Google Drive video…</p><a id="videoDriveOpen" class="text-link" hidden target="_blank" rel="noreferrer">Buka folder Google Drive</a></div><img id="videoQrImage" class="drive-qr-image" alt="QR Code hasil video" hidden></section><div class="result-share-controls"><div class="form-grid"><div class="field"><label>Nomor WhatsApp pelanggan</label><input id="videoCustomerWhatsApp" placeholder="08xxxxxxxxxx" inputmode="tel" autocomplete="tel"></div><div class="field"><label>Email pelanggan</label><input id="videoCustomerEmail" placeholder="nama@email.com" type="email"></div></div><div class="actions wrap"><button id="videoShareWhatsApp" class="btn whatsapp-share">Kirim Link WhatsApp</button><button id="videoShareEmail" class="btn secondary">Share via Email</button><a class="btn secondary" id="videoDownload" href="http://127.0.0.1:8765/api/video/${videoKey}/download.mp4" download="KACA-ID-Video-${videoKey}.mp4">Unduh MP4</a></div><label class="field-help" style="display:flex;gap:9px;align-items:flex-start;margin-top:12px"><input type="checkbox" id="videoConsent"> Pelanggan menyetujui menerima tautan video melalui WhatsApp.</label><div class="notice" id="videoShareStatus">Video sudah tersimpan lokal; tautan WhatsApp tersedia setelah folder Drive dibuat.</div></div></section></div><div class="result-return-bar"><div>Kembali ke Dashboard dalam <b id="videoReturnCountdown">${Math.max(5,Number(settings.resultReturnSeconds)||30)}</b> detik</div><button id="videoFinishNow" class="btn">SELESAI</button></div></div>`;
   const poster=$v('#videoResultPoster');poster.src=`http://127.0.0.1:8765/api/video/${videoKey}/poster.jpg?v=${Date.now()}`;const video=$v('#videoResultPlayer');video.controls=false;video.style.pointerEvents='none';video.src=url;video.load();video.onerror=()=>{$v('#videoShareStatus').textContent='Preview video tidak dapat diputar oleh Electron. MP4 tersimpan lokal dan tersedia lewat tombol Unduh MP4; QR tetap dapat digunakan.';};video.play().catch(e=>{console.warn('[VIDEO_FINAL_AUTOPLAY]',e);});
   $v('#videoFinishNow').onclick=leave;
   const total=Math.max(5,Math.min(600,Number(settings.resultReturnSeconds)||30)),deadline=Date.now()+total*1000;
   videoTimer=setInterval(()=>{if(root!==$('#content')){stopPolling();return;}const remaining=Math.max(0,Math.ceil((deadline-Date.now())/1000));if($v('#videoReturnCountdown'))$v('#videoReturnCountdown').textContent=String(remaining);if(!remaining)leave();},1000);
   const showDrive=async()=>{if(root!==$('#content')||!videoId||videoId!==videoKey)return;try{const d=await api(`/api/video/${encodeURIComponent(videoKey)}/status`);if(d.drive_url){driveShareUrl=d.drive_url;$v('#videoDriveOpen').href=d.drive_url;$v('#videoDriveOpen').hidden=false;}if(d.qr_available){const image=$v('#videoQrImage');if(image.hidden||!image.src.includes('/qr.png')){image.onload=()=>{image.hidden=false;$v('#videoDriveStatus').textContent=d.drive_status==='ready'?'QR siap — video tersedia di Google Drive.':'QR siap — upload video sedang diproses.';};image.onerror=()=>{$v('#videoDriveStatus').textContent='QR belum dapat dibuka, sistem mencoba kembali.';};image.src=d.qr_url+'?v='+Date.now();}}else if(!d.drive_url){$v('#videoDriveStatus').textContent=d.drive_status==='waiting_auth'?'Google Drive belum terhubung. Hasil video sudah disimpan lokal.':'Membuat folder Google Drive dan QR video…';}else{$v('#videoDriveStatus').textContent='Folder tersedia. Menyiapkan QR video…';}if(d.drive_error)$v('#videoShareStatus').textContent='Google Drive: '+d.drive_error;}catch(e){$v('#videoDriveStatus').textContent='Memeriksa ulang koneksi Google Drive…';}};
   void showDrive();drivePolling=setInterval(showDrive,2500);
   $v('#videoShareWhatsApp').onclick=async()=>{const btn=$v('#videoShareWhatsApp'),notice=$v('#videoShareStatus'),phone=$v('#videoCustomerWhatsApp').value.trim();if(!phone){notice.textContent='Masukkan nomor WhatsApp penerima.';return;}if(!$v('#videoConsent').checked){notice.textContent='Minta persetujuan pelanggan terlebih dahulu.';return;}if(!driveShareUrl){notice.textContent='Tautan Google Drive belum tersedia. Coba lagi setelah folder siap.';return;}try{btn.disabled=true;if(settings.waDeliveryMode==='gateway_fonnte'){const response=await api('/api/whatsapp/fonnte/send',{method:'POST',body:JSON.stringify({kind:'video',video_id:videoKey,phone,consent:true})});notice.textContent=response.duplicate?'Permintaan sebelumnya telah diterima gateway.':'Gateway menerima permintaan. Status diterima pelanggan belum dapat dipastikan.';}else if(settings.waDeliveryMode==='click_to_chat'){const digits=phone.replace(/\D/g,'');const normalized=digits.startsWith('0')?'62'+digits.slice(1):digits.startsWith('8')?'62'+digits:digits;if(!/^62\d{8,13}$/.test(normalized))throw new Error('Nomor WhatsApp tidak valid.');await window.kaca.openExternal('https://wa.me/'+normalized+'?text='+encodeURIComponent('Hasil video KACA STUDIO: '+driveShareUrl));notice.textContent='WhatsApp terbuka. Tekan Kirim pada perangkat Anda.';}else{const response=await api('/api/whatsapp/send',{method:'POST',body:JSON.stringify({kind:'video',video_id:videoKey,phone,consent:true})});notice.textContent=response.duplicate?'Sudah berada dalam antrean WhatsApp.':'Pengiriman masuk antrean WhatsApp.';}}catch(e){notice.textContent='Gagal mengirim: '+e.message;}finally{btn.disabled=false;}};
   $v('#videoShareEmail').onclick=()=>{const email=$v('#videoCustomerEmail').value.trim();if(!email||!email.includes('@')){$v('#videoShareStatus').textContent='Masukkan alamat email yang valid.';return;}if(!driveShareUrl){$v('#videoShareStatus').textContent='Tautan Google Drive belum siap.';return;}window.location.href='mailto:'+encodeURIComponent(email)+'?subject='+encodeURIComponent('Video KACA STUDIO')+'&body='+encodeURIComponent('Hasil video Anda: '+driveShareUrl);};
 };
 try{await prepareFrames();const hasTransactions=settings.enableVoucherPayment!==false||settings.enableQrisPayment!==false;root.classList.toggle('skip-transaction',!hasTransactions);if(hasTransactions){setStage(1);hideLoading();}else await showVideoFrameStep();}catch(e){showLoading('Gagal memuat frame: '+e.message);$v('#videoRetryFrames').hidden=false;}
}

async function renderCapture(){
 const mode=settings.sessionMode||'fixed_count';const frameSlots=Number(settings.frameSlots||4);const durationMinutes=Number(settings.sessionDurationMinutes||5);
 $('#content').innerHTML=`<div class="capture-grid"><div class="panel"><div class="eyebrow2">KACA.ID / CAPTURE STUDIO</div><h3>Sesi Pemotretan</h3><div class="capture-preview" id="capturePreview" style="--preview-button-color:${settings.boothButtonColor||settings.accentColor||'#d8b56a'};--preview-button-opacity:${Math.max(10,Math.min(100,Number(settings.boothButtonOpacity??88)))/100};--preview-button-scale:${Math.max(70,Math.min(140,Number(settings.boothButtonScale??100)))/100}"><img id="captureLive" alt="Live webcam"><div id="captureNoVideo">Live preview belum tersedia. Aktifkan kamera di menu Perangkat.</div><div id="countOverlay" class="count-overlay" hidden></div><div class="preview-timer" id="previewTimer" hidden>05:00</div><button class="preview-start-button" id="flowStart">MULAI SESI</button><button class="preview-capture-start" id="flowCaptureStart" hidden>MULAI PEMOTRETAN</button><div class="preview-tools"><input type="checkbox" id="mirrorToggle" ${settings.mirrorPreview?'checked':''} hidden></div><button type="button" class="preview-icon-button preview-mirror-button" id="mirrorButton" title="Mirror kamera" aria-label="Mirror kamera"><img class="preview-icon-asset" src="assets/mirror-camera.svg" alt=""></button><button type="button" class="preview-angle-switch" id="captureAngleSwitch" role="switch" aria-checked="${Number(settings.activeCameraAngle||0)===1?'true':'false'}" aria-label="Ganti kamera" ${settings.multicamEnabled?'':'hidden'}><span class="angle-switch-label angle-label-one">KAMERA 1</span><span class="angle-switch-label angle-label-two">KAMERA 2</span><span class="angle-switch-knob"></span></button><div class="preview-bottom-controls"><button type="button" class="preview-tool-button" id="takePhoto" disabled>AMBIL FOTO</button></div></div><div class="capture-settings"><div class="field"><label>Countdown Capture</label><select id="shotCountdown" ${settings.livePhotoEnabled?'disabled':''}>${(settings.livePhotoEnabled?[5,10,15,20,25,30]:[0,3,5,10]).map(n=>`<option value="${n}" ${Number(settings.livePhotoEnabled?(settings.livePhotoDuration||5):(settings.countdown??3))===n?'selected':''}>${n===0?'Tanpa countdown':n+' detik'}</option>`).join('')}</select><small class="field-help">${settings.livePhotoEnabled?'Mengikuti durasi Live Photo pada Pengaturan Sesi.':'Countdown foto biasa.'}</small></div></div><div class="timer-display" id="sessionTimer" hidden>05:00</div><div class="actions wrap"><button class="btn secondary" id="startSession" hidden>Mulai Sesi</button><button class="btn secondary" id="endCapture" disabled>Akhiri & Pilih Foto</button><button class="btn secondary" id="finishSession" disabled hidden></button></div><div id="captureStatus" class="notice">Memeriksa kamera aktif…</div><div id="livePhotoStatus" class="notice">Live Photo: belum ada sesi aktif.</div></div><div class="panel"><div class="session-photos-heading"><div><div class="eyebrow2">SESSION PHOTOS</div><h3>Foto dalam Sesi</h3></div><button type="button" class="btn secondary session-retake-button" id="retakePhoto" title="Ulangi foto terakhir" aria-label="Ulangi foto terakhir" disabled>↶ RETAKE</button></div><div class="progress-track"><div id="shotProgress"></div></div><div id="shotCounter" class="shot-counter">0 foto</div><div id="selectionControls" class="selection-controls" hidden><small class="field-help">Pilih foto untuk mengisi slot frame. Foto yang sama dapat dipilih lebih dari sekali.</small></div><div id="shotGallery" class="shot-gallery"><div class="empty">Belum ada foto. Mulai sesi untuk mengambil gambar.</div></div><div id="finishedResult"></div></div></div>`;
 const root=$('#content');root.classList.add('photo-session-content');const captureGrid=root.querySelector('.capture-grid');captureGrid.id='captureGrid';
 // v0.9.87: camera preview / shot strip / original controls in distinct rows.
 // Moving the *actual* button nodes preserves their old handlers and switch model.
 const captureFirst=captureGrid.querySelector('.panel:first-child');
 // Keep capture progress accessible to screen readers but remove text above preview.
 captureFirst.insertAdjacentHTML('afterbegin',`<span class="photo-progress-sr-only" id="photoCaptureProgress" role="status" aria-live="polite">Ambil Foto (1 / ${Math.max(1,frameSlots)})</span>`);
 const captureToolbar=document.createElement('div');captureToolbar.className='photo-capture-toolbar';
 const oldSwitch=captureGrid.querySelector('#captureAngleSwitch'),oldMirror=captureGrid.querySelector('#mirrorButton');
 const oldShutter=captureGrid.querySelector('.preview-bottom-controls'),oldRetake=captureGrid.querySelector('#retakePhoto');
 const controlStart=document.createElement('div');controlStart.className='photo-toolbar-left';
 for(const node of [oldSwitch,oldMirror])if(node)controlStart.appendChild(node);
 captureToolbar.appendChild(controlStart);
 for(const node of [oldShutter,oldRetake])if(node)captureToolbar.appendChild(node);
 // The original switch, mirror, shutter and retake nodes are overlaid on
 // the video itself. Moving nodes retains their existing event handlers.
 captureGrid.querySelector('#capturePreview').appendChild(captureToolbar);
 const syncPhotoCaptureCount=()=>{
   const heading=captureGrid.querySelector('#photoCaptureProgress');
   const tray=captureGrid.querySelector('#shotGallery');
   if(heading&&tray)heading.textContent=`Ambil Foto (${Math.min(Math.max(1,frameSlots),tray.querySelectorAll('.shot-thumb').length+1)} / ${Math.max(1,frameSlots)})`;
 };
 const photoShotGallery=captureGrid.querySelector('#shotGallery');
 if(photoShotGallery)new MutationObserver(syncPhotoCaptureCount).observe(photoShotGallery,{childList:true});
const captureGridParking=document.createDocumentFragment();// v0.9.65: the results panel is moved out of captureGrid for slide 5.
 // Keep all result element lookups valid after that move (including QR/video callbacks).
 const $cap=id=>captureGrid.querySelector(id)||root.querySelector(id);captureGridParking.appendChild(captureGrid);const mirrorToggleEl=captureGrid.querySelector('#mirrorToggle'),angleSwitchEl=captureGrid.querySelector('#captureAngleSwitch');if(!mirrorToggleEl||!angleSwitchEl)throw new Error('Kontrol kamera tidak lengkap pada template sesi.');
 root.insertAdjacentHTML('afterbegin',`<div class="photo-flow-head"><div><div class="eyebrow2">KACA.ID / CUSTOMER PHOTO SESSION</div><h2 id="flowTitle">Pilih Metode Transaksi</h2><p id="flowSubtitle">Pilih Voucher atau QRIS untuk melanjutkan sesi.</p></div><button class="btn secondary" id="flowExit">Keluar dari Sesi</button></div><div class="photo-flow-steps"><div data-step-label="1" class="flow-step active"><b>01</b><span>Transaksi</span></div><div data-step-label="2" class="flow-step"><b>02</b><span>Pilih Frame</span></div><div data-step-label="3" class="flow-step"><b>03</b><span>Foto</span></div><div data-step-label="4" class="flow-step"><b>04</b><span>Filter</span></div><div data-step-label="5" class="flow-step"><b>05</b><span>Hasil</span></div></div><div class="flow-action-row" id="flowActions"><button class="btn" id="flowFrameNext" hidden>LANJUT</button><button class="btn" id="flowFilterNext" hidden>LANJUT KE HASIL</button></div><section class="transaction-method-panel" id="flowTransactionPanel"><div class="transaction-method-title">PILIH METODE TRANSAKSI</div><div class="transaction-method-options"><button type="button" class="transaction-method-choice" data-transaction-method="voucher"><span class="transaction-voucher-mark">VOUCHER</span><b>Voucher</b></button><button type="button" class="transaction-method-choice" data-transaction-method="qris"><span class="transaction-qris-mark">QRIS</span><b>QRIS</b></button></div></section>`);
 root.insertAdjacentHTML('beforeend',`<div class="flow-slide-loading" id="flowSlideLoading" hidden role="status" aria-live="polite"><div class="flow-slide-loading-spinner"></div><strong>Tunggu kakak...😊</strong><span id="flowSlideLoadingText">Menyiapkan slide hingga siap ditampilkan…</span><div class="flow-frame-load-progress" id="flowFrameLoadProgress" hidden><div id="flowFrameLoadBar"></div></div><button class="btn secondary" type="button" id="flowFrameRetry" hidden>Coba Muat Frame Lagi</button><div class="flow-result-loading-actions" id="flowResultLoadingActions" hidden><button class="btn" type="button" id="flowResultSkip">Lewati Proses → Hasil Sesi</button><button class="btn secondary" type="button" id="flowResultRetry">Coba Lagi</button><button class="btn secondary" type="button" id="flowResultDashboard">Kembali ke Dashboard</button></div></div>`);
 root.insertAdjacentHTML('beforeend',`<div class="panel flow-frame-panel" id="flowFramePanel" hidden><div class="flow-frame-heading"><div class="eyebrow2">KACA.ID / FRAME STUDIO</div><h3>Pilih Frame Foto</h3><p class="muted">Pilih desain frame yang tersedia untuk sesi foto Anda.</p></div><div class="flow-frame-layout"><div class="flow-frame-list-wrap"><div class="flow-frame-list-label">DAFTAR FRAME</div><div class="flow-frame-grid" id="flowFrameGrid"><div class="empty">Memuat frame…</div></div></div><div class="flow-frame-preview-wrap"><div class="flow-frame-preview-label">PREVIEW FRAME TERPILIH</div><div class="flow-frame-preview-stage"><img id="flowFramePreviewImage" alt="Preview frame terpilih" hidden></div><div id="flowFrameNextMount"></div><div class="notice flow-frame-status" id="flowFrameStatus" role="status" aria-live="polite">Pilih frame, lalu tekan Lanjut.</div></div></div></div>`);
 root.insertAdjacentHTML('beforeend',`<section class="filter-review-panel" id="flowFilterPanel" hidden><div class="filter-review-head"><div><div class="eyebrow2">KACA.ID / FILTER STUDIO</div><h3>Atur Nuansa Foto</h3><p>Pilih filter di kanan. Pratinjau di kiri menampilkan foto yang sudah tersusun di dalam frame.</p></div></div><div class="filter-review-layout"><div class="filter-preview-column"><div class="filter-preview-frame"><canvas id="filterPreviewCanvas" aria-label="Pratinjau foto dalam frame"></canvas><div id="filterPreviewEmpty" hidden>Foto akan tampil di sini setelah sesi pemotretan.</div></div><div class="filter-preview-caption" id="filterPreviewCaption">PREVIEW HASIL CETAK · PROPORSI FRAME DIPERTAHANKAN</div></div><div class="filter-photo-column"><div class="filter-picker-title">PILIH FOTO</div><div class="filter-photo-picker" id="filterPhotoPicker" hidden></div></div><div class="filter-picker-column"><div class="filter-actions-sticky"><button type="button" class="btn secondary filter-retake-button" id="filterRetake">↶ ULANGI FOTO TERAKHIR</button></div><div class="filter-picker-title">PILIH FILTER</div><div class="filter-picker-scroll"><div class="filter-picker-grid" id="flowFilterChoices"></div></div><div id="filterNextMount" class="filter-next-footer"></div><div class="filter-selected-note" id="flowFilterNote">Filter diterapkan ke foto hasil. Foto original tetap tersimpan tanpa perubahan.</div></div></div></section>`);
 const filterNextMount=$('#filterNextMount');if(filterNextMount)filterNextMount.appendChild($('#flowFilterNext')); $('#flowFilterNext').classList.add('filter-next-inline');const frameNextMount=$('#flowFrameNextMount');if(frameNextMount)frameNextMount.appendChild($('#flowFrameNext'));
 let flowStep=0,flowSlideLoadingTimer=null;const showFlowSlideLoading=(n)=>{
  const loader=$('#flowSlideLoading'),label=$('#flowSlideLoadingText');if(!loader)return;
  if(flowSlideLoadingTimer){clearTimeout(flowSlideLoadingTimer);flowSlideLoadingTimer=null;}
  if(![0,2,4,'result'].includes(n)){loader.hidden=true;return;}
  loader.hidden=false;
  if(label)label.textContent=n===0?'Menyiapkan frame preset dan alur sesi…':n===2?'Memeriksa frame dari Pengaturan/Event…':n===4?'Memuat preview foto dan frame…':'Menyiapkan pemutaran Live Photo dalam frame…';
  // Final result must never be revealed merely because 15 seconds elapsed.
  if(n===4)flowSlideLoadingTimer=setTimeout(()=>{loader.hidden=true;},15000);
};
const hideFlowSlideLoading=()=>{const loader=$('#flowSlideLoading');if(loader)loader.hidden=true;if(flowSlideLoadingTimer){clearTimeout(flowSlideLoadingTimer);flowSlideLoadingTimer=null;}};
const setFlowStep=(n)=>{flowStep=n;root.dataset.flowStep=String(n);showFlowSlideLoading(n);const names={1:['Pilih Metode Transaksi','Pilih Voucher atau QRIS untuk melanjutkan sesi.'],2:['Pilih Frame','Pilih desain frame yang akan digunakan untuk hasil foto.'],3:['Sesi Pemotretan','Ikuti hitung mundur untuk mengambil foto.'],4:['Pilih Filter','Periksa foto dan tentukan tampilan hasil akhir.'],5:['Hasil Sesi','Semua hasil sesi siap dicetak dan dibagikan.']};$('#flowTitle').textContent=names[n][0];$('#flowSubtitle').textContent=names[n][1];root.querySelectorAll('[data-step-label]').forEach(el=>{const k=Number(el.dataset.stepLabel);el.classList.toggle('active',k===n);el.classList.toggle('done',k<n);});$cap('#flowStart').hidden=true;$('#flowFrameNext').hidden=n!==2;$cap('#flowCaptureStart').hidden=true;$('#flowFilterNext').hidden=n!==4;take.hidden=n!==3||!session;$('#flowTransactionPanel').hidden=n!==1;$('#flowFramePanel').hidden=n!==2;$('#flowFilterPanel').hidden=n!==4;if(n===3){if(captureGrid.parentElement!==root)root.appendChild(captureGrid);captureGrid.hidden=false;}else{if(captureGrid.parentElement!==captureGridParking)captureGridParking.appendChild(captureGrid);captureGrid.hidden=true;}$('#flowActions').hidden=n===1||n===3||n===4||n===5;if(n===5){const result=$cap('#finishedResult');if(result&&result.parentElement!==root)root.appendChild(result);}if(n===4){drawFilterReview();scheduleBackgroundRender();}};
 root.dataset.flowStep='0';showFlowSlideLoading(0);
let selectedTransactionMethod='',redeemedVoucherCode='',paidQrisInvoice='',captureUiReady=false;const transactionPanel=$('#flowTransactionPanel');transactionPanel.hidden=true;transactionPanel.querySelectorAll('[data-transaction-method]').forEach(btn=>{const enabled=btn.dataset.transactionMethod==='voucher'?settings.enableVoucherPayment!==false:settings.enableQrisPayment!==false;btn.hidden=!enabled;btn.disabled=true;btn.setAttribute('aria-disabled','true');});transactionPanel.querySelectorAll('[data-transaction-method]').forEach(btn=>btn.onclick=async()=>{if(!captureUiReady){status.textContent='Menyiapkan kamera dan sesi. Tunggu sebentar lalu coba kembali.';return;}const method=btn.dataset.transactionMethod;try{if(method==='voucher'){const code=await requestVoucherCode();if(code===null)return;const result=await api('/api/vouchers/validate',{method:'POST',body:JSON.stringify({code})});if(!result.ok)throw new Error(result.error||'Voucher tidak valid.');redeemedVoucherCode=result.voucher.code;selectedTransactionMethod='voucher';alert('Voucher valid. Sisa penggunaan setelah sesi dimulai: '+result.remaining_uses+'.');}else{const q=await api('/api/qris/status');if(!q.configured)throw new Error('QRIS belum dikonfigurasi admin. Buka menu Pembayaran.');
 if(q.mode==='doku_checkout'){
   const checkout=await api('/api/qris/checkout/create',{method:'POST',body:'{}'});
   const gate=document.createElement('div');gate.className='session-pin-overlay';
   gate.innerHTML=`<div class="session-pin-card qris-online-card"><h3>Bayar QRIS — Rp ${Number(checkout.amount).toLocaleString('id-ID')}</h3><p>Scan QRIS pada halaman DOKU berikut. Setelah pembayaran berhasil dikonfirmasi DOKU, aplikasi akan otomatis lanjut.</p><iframe id="dokuCheckoutFrame" title="Pembayaran QRIS DOKU" src="${esc(checkout.checkout_url)}" loading="eager" referrerpolicy="no-referrer" sandbox="allow-scripts allow-forms allow-same-origin allow-popups"></iframe><p id="dokuCheckoutProgress" class="notice">Menunggu pembayaran. Pemeriksaan transaksi mulai setelah 60 detik sesuai rekomendasi DOKU.</p><div class="actions"><button type="button" class="btn secondary" data-doku-open>Tampilkan QRIS di KACA.ID</button><button type="button" class="btn secondary" data-doku-cancel>Batalkan</button></div></div>`;
   document.body.appendChild(gate);
   let polling=false,closed=false;
   const clean=()=>{closed=true;clearInterval(timer);window.kaca.closeQrisCheckout?.().catch(()=>{});gate.remove();};
   gate.querySelector('[data-doku-cancel]').onclick=clean;
   gate.querySelector('[data-doku-open]').onclick=()=>window.kaca.openQrisCheckout(checkout.checkout_url).catch(e=>{gate.querySelector('#dokuCheckoutProgress').textContent='Gagal membuka Checkout DOKU di KACA.ID: '+e.message;});
   const check=async()=>{if(closed||polling)return;polling=true;try{
     const st=await api('/api/qris/checkout/status?invoice='+encodeURIComponent(checkout.invoice));
     if(st.status==='paid'){
       clean();selectedTransactionMethod='qris_doku';paidQrisInvoice=checkout.invoice;redeemedVoucherCode='';
       transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));
       void showPreparedFrameStep();
     } else if(['expired','failed'].includes(st.status)){
       gate.querySelector('#dokuCheckoutProgress').textContent='Pembayaran '+st.status+'. Batalkan lalu coba transaksi baru.';
       clearInterval(timer);
     } else {
       gate.querySelector('#dokuCheckoutProgress').textContent='Menunggu konfirmasi pembayaran dari DOKU… Invoice '+checkout.invoice;
     }
   }catch(e){gate.querySelector('#dokuCheckoutProgress').textContent='Pemeriksaan pembayaran: '+e.message;}finally{polling=false;}};
   const timer=setInterval(check,10000);void check();return;
 }
 const gate=document.createElement('div');gate.className='session-pin-overlay';gate.innerHTML=`<div class="session-pin-card qris-customer-card"><div class="eyebrow2">PEMBAYARAN QRIS</div><h3>${esc(q.merchant_name||'KACA.ID')}</h3><img src="http://127.0.0.1:8765/api/qris/image?v=${Date.now()}" alt="QRIS" style="display:block;max-width:260px;max-height:260px;object-fit:contain;background:white;padding:12px;margin:16px auto;border-radius:12px"><b>Rp ${Number(q.amount||settings.sessionPrice||0).toLocaleString('id-ID')}</b><p>${esc(q.instructions||'Scan QRIS dan tunjukkan bukti pembayaran kepada operator.')}</p><p class="field-help">Sesi hanya dapat dilanjutkan setelah operator memeriksa pembayaran.</p><input type="password" id="qrisOperatorPin" placeholder="PIN operator" inputmode="numeric"><div class="actions"><button type="button" class="btn secondary" data-qris-cancel>Batal</button><button type="button" class="btn" data-qris-approve>Operator: verifikasi & lanjut</button></div><small class="pin-error" id="qrisPinError"></small></div>`;document.body.appendChild(gate);gate.querySelector('[data-qris-cancel]').onclick=()=>gate.remove();gate.querySelector('[data-qris-approve]').onclick=()=>{if(gate.querySelector('#qrisOperatorPin').value!==String(settings.adminPin||'1234')){gate.querySelector('#qrisPinError').textContent='PIN operator salah.';return;}gate.remove();selectedTransactionMethod='qris_manual';redeemedVoucherCode='';transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));void showPreparedFrameStep();};return;}transactionPanel.querySelectorAll('.transaction-method-choice').forEach(x=>x.classList.toggle('selected',x===btn));void showPreparedFrameStep();}catch(e){alert(e.message);}});
 const getFrameLayout=(frameId)=>{const saved=frameId&&(settings.frameLayouts&&settings.frameLayouts[frameId]);if(Array.isArray(saved)&&saved.length)return saved.map(v=>({...v}));if(String(frameId||'')===String(settings.frameId||'')&&Array.isArray(settings.layoutSlots)&&settings.layoutSlots.length)return settings.layoutSlots.map(v=>({...v}));return [];};
 const flowFrames=await api('/api/frames').catch(err=>({frames:[],loadError:err.message||String(err)}));const availableFrames=(flowFrames.frames||[]).filter(f=>f.enabled!==false && f.active!==false && frameBelongsToCurrentEvent(f));const configuredPhotoFrame=availableFrames.find(f=>f.id===settings.frameId)||availableFrames[0];const activeFrameList=availableFrames;let chosenFrameId=configuredPhotoFrame?.id||'';const frameGrid=$('#flowFrameGrid');const refreshChosenFrameInfo=()=>{const preview=$('#flowFramePreviewImage');if(preview&&chosenFrameId){preview.onload=()=>{};preview.onerror=()=>{$('#flowFrameStatus').textContent='Preview frame gagal dimuat; coba pilih ulang.';};preview.src=`http://127.0.0.1:8765/api/frames/${chosenFrameId}.png`;preview.hidden=false;}else if(preview){preview.removeAttribute('src');preview.hidden=true;}};frameGrid.innerHTML=activeFrameList.map(f=>`<button class="flow-frame-choice ${chosenFrameId===f.id?'chosen':''}" data-frame-id="${f.id}" aria-label="Pilih frame"><img loading="eager" decoding="async" src="http://127.0.0.1:8765/api/frames/${f.id}.png" alt="Frame"></button>`).join('')||( '<div class="empty">Belum ada frame PNG aktif. Tambahkan frame melalui menu Frame & Layout.</div>');const frameNextButton=$('#flowFrameNext');frameNextButton.disabled=!chosenFrameId||!activeFrameList.length;// Photo mode intentionally retains customer Frame Selection; video mode skips it.
frameGrid.querySelectorAll('[data-frame-id]').forEach(card=>card.onclick=()=>{
 chosenFrameId=card.dataset.frameId;
 frameGrid.querySelectorAll('.flow-frame-choice').forEach(el=>el.classList.toggle('chosen',el===card));
 frameNextButton.disabled=false;
 refreshChosenFrameInfo();
 const selected=activeFrameList.find(f=>f.id===chosenFrameId);
 const name=$('#flowFramePreviewName');if(name)name.textContent=selected?.name||'Frame Terpilih';
 const note=$('#flowFrameNotice');if(note)note.textContent='Frame '+(selected?.name||chosenFrameId)+' dipilih. Tekan LANJUT untuk memulai foto.';
});refreshChosenFrameInfo();
 // Preload *every* enabled frame before step 2 is shown. Hidden lazy images
// are not dependable here; decode using Image() and show measured progress.
let frameReadyPromise=null,frameLoadRunning=false,frameLoadedCount=0,framePreloadedSuccessfully=false;
const frameLoadingLabel=$('#flowSlideLoadingText'),frameRetry=$('#flowFrameRetry'),frameProgress=$('#flowFrameLoadProgress'),frameBar=$('#flowFrameLoadBar');
const updateFrameLoading=(done,total,message)=>{
  frameLoadedCount=done;
  if(frameLoadingLabel)frameLoadingLabel.textContent=message||`Menyiapkan frame ${done} dari ${total}…`;
  if(frameProgress)frameProgress.hidden=false;
  if(frameBar)frameBar.style.width=(total?Math.round(done/total*100):100)+'%';
};
const checkFrameImage=(f,retry=0)=>new Promise(resolve=>{
  const image=new Image();let settled=false;
  const finish=ok=>{if(settled)return;settled=true;clearTimeout(timeout);image.onload=null;image.onerror=null;resolve(ok);};
  const timeout=setTimeout(()=>finish(false),8500);
  image.onload=async()=>{
    if(!image.naturalWidth||!image.naturalHeight){finish(false);return;}
    if(typeof image.decode==='function'){
      try{await image.decode();}catch(e){finish(false);return;}
    }
    finish(true);
  };
  image.onerror=()=>finish(false);
  image.src=`http://127.0.0.1:8765/api/frames/${encodeURIComponent(f.id)}.png${retry?'?retry='+Date.now():''}`;
});
const preloadAllFrames=()=>{
  if(frameReadyPromise)return frameReadyPromise;
  frameReadyPromise=(async()=>{
    if(!activeFrameList.length)return {ok:!activeEvent(),missing:activeEvent()?['Belum ada frame pada event aktif']:[]};
    let cursor=0,done=0;const missing=[];
    updateFrameLoading(0,activeFrameList.length);
    const worker=async()=>{
      while(cursor<activeFrameList.length){
        const f=activeFrameList[cursor++];
        let ok=await checkFrameImage(f);
        if(!ok)ok=await checkFrameImage(f,1);
        if(!ok)missing.push(String(f.id));
        done++;updateFrameLoading(done,activeFrameList.length,
          `Menyiapkan frame ${done} dari ${activeFrameList.length}…`);
      }
    };
    await Promise.all(Array.from({length:Math.min(4,activeFrameList.length)},()=>worker()));
    if(missing.length)return {ok:false,missing};
    // Do not reveal the frame page until the actual card images are decoded.
    const cardImages=[...frameGrid.querySelectorAll('img')];
    const decoded=await Promise.all(cardImages.map(im=>new Promise(resolve=>{
      im.loading='eager';im.decoding='async';
      if(im.complete&&im.naturalWidth>0){
        Promise.resolve(typeof im.decode==='function'?im.decode():null).then(()=>resolve(true)).catch(()=>resolve(false));return;
      }
      let settled=false;
      const timer=setTimeout(()=>finish(false),8500);
      const finish=ok=>{if(settled)return;settled=true;clearTimeout(timer);im.removeEventListener('load',onLoad);im.removeEventListener('error',onError);resolve(ok);};
      const onLoad=()=>{if(im.naturalWidth>0){
        Promise.resolve(typeof im.decode==='function'?im.decode():null).then(()=>finish(true)).catch(()=>finish(false));
      }else finish(false);};
      const onError=()=>finish(false);
      im.addEventListener('load',onLoad);im.addEventListener('error',onError);
      // A hidden eager image may have received a transient 503 *before* the
      // separate preload succeeded. Retry that specific DOM card now.
      if(im.complete && !im.naturalWidth){
        const baseUrl=im.src.split('?')[0];
        im.src=baseUrl+'?retryCard='+Date.now();
      }
    })));
    const unavailable=activeFrameList.filter((_,i)=>!decoded[i]).map(f=>String(f.id));
    return {ok:unavailable.length===0,missing:unavailable};
  })();
  return frameReadyPromise;
};
const showPreparedFrameStep=async()=>{
  if(frameLoadRunning||root!==$('#content'))return;
  frameLoadRunning=true;
  if(!framePreloadedSuccessfully)showFlowSlideLoading(2);
  if(frameRetry)frameRetry.hidden=true;
  updateFrameLoading(frameLoadedCount,activeFrameList.length);
  try{
    const result=await preloadAllFrames();
    if(root!==$('#content'))return;
    if(!result.ok){
      frameReadyPromise=null;
      if(frameLoadingLabel)frameLoadingLabel.textContent=
        `${result.missing.length} frame belum berhasil dimuat. Periksa koneksi backend dan tekan Coba Muat Frame Lagi.`;
      if(frameRetry)frameRetry.hidden=false;
      return;
    }
    framePreloadedSuccessfully=true;
    setFlowStep(2);
    hideFlowSlideLoading();
    if(frameProgress)frameProgress.hidden=true;
    if(frameRetry)frameRetry.hidden=true;
    const notice=$('#flowFrameStatus');
    if(notice)notice.textContent=`${activeFrameList.length} frame tersedia. Pilih frame lalu tekan LANJUT.`;
  }catch(err){
    frameReadyPromise=null;
    if(frameLoadingLabel)frameLoadingLabel.textContent='Gagal menyiapkan frame: '+err.message;
    if(frameRetry)frameRetry.hidden=false;
  }finally{frameLoadRunning=false;}
};
if(frameRetry)frameRetry.onclick=showPreparedFrameStep;
// Preloading begins as part of the post-dashboard gate below; never expose
// the transaction slide (or the frame slide) while frame assets are pending.
const angleSwitch=angleSwitchEl;const syncAngleSwitch=()=>{const angle=Number(settings.activeCameraAngle||0);angleSwitch.classList.toggle('camera-two-active',angle===1);angleSwitch.setAttribute('aria-checked',angle===1?'true':'false');angleSwitch.title=angle===1?'Kamera 2 aktif — tekan untuk Kamera 1':'Kamera 1 aktif — tekan untuk Kamera 2';};if(settings.multicamEnabled){angleSwitch.hidden=false;angleSwitch.disabled=!settings.multicamCamera2Ready;}else angleSwitch.hidden=true;syncAngleSwitch();angleSwitch.onclick=async()=>{if(angleSwitch.disabled)return;try{const angle=Number(settings.activeCameraAngle||0)===0?1:0;if(angle===1&&!settings.multicamCamera2Ready)throw new Error('Kamera 2 belum siap. Periksa pengaturan MultiCam.');angleSwitch.disabled=true;await api('/api/camera/angle',{method:'POST',body:JSON.stringify({angle})});settings.activeCameraAngle=angle;await saveScopedSettings();syncAngleSwitch();live.src=`http://127.0.0.1:8765/${angle===1?'api/stream-secondary.mjpg':'api/stream.mjpg'}?angle=${Date.now()}`;applyPhotoAngleOrientation();status.textContent=`${angle===0?'Kamera 1':'Kamera 2'} aktif.`;}catch(e){status.textContent='Gagal mengganti kamera: '+e.message;}finally{angleSwitch.disabled=!settings.multicamEnabled||!settings.multicamCamera2Ready&&Number(settings.activeCameraAngle||0)===0;}};
 $cap('#flowStart').onclick=()=>{void showPreparedFrameStep();};const beginConfiguredPhotoSession=async()=>{const btn=$('#flowFrameNext');if(btn.disabled)return;if(!chosenFrameId){status.textContent='Belum ada frame PNG aktif. Tambahkan frame terlebih dahulu.';return;}btn.disabled=true;btn.textContent='MENYIAPKAN KAMERA…';const frameNotice=$('#flowFrameStatus');if(frameNotice)frameNotice.textContent='Mengaktifkan kamera dan menyiapkan sesi…';try{const previousFrameId=settings.frameId||'';const selectedLayout=getFrameLayout(chosenFrameId);settings.frameId=chosenFrameId;if(selectedLayout.length){settings.layoutSlots=selectedLayout;settings.frameSlots=String(selectedLayout.length);}else if(String(chosenFrameId||'')!==String(previousFrameId)){settings.layoutSlots=[];}await saveScopedSettings();await ensureCaptureCamera();if(typeof start.onclick!=='function')throw new Error('Handler sesi belum siap.');start.dataset.lastError='';await start.onclick();if(!session)throw new Error(start.dataset.lastError||$cap('#captureStatus')?.textContent||'Backend belum mengonfirmasi sesi aktif.');setFlowStep(3);take.hidden=false;status.textContent='Sesi aktif. Tekan AMBIL FOTO untuk mengambil foto.';if(frameNotice)frameNotice.textContent='Kamera siap. Sesi pemotretan dimulai.';}catch(e){if(frameNotice)frameNotice.textContent='Tidak dapat melanjutkan: '+e.message;status.textContent='Tidak dapat melanjutkan: '+e.message;if(frameLoadingLabel)frameLoadingLabel.textContent='Kamera belum siap: '+e.message;if(frameRetry){frameRetry.hidden=false;frameRetry.textContent='Coba Lagi';}}finally{btn.textContent='LANJUT';btn.disabled=!activeFrameList.length||!!session;}};$('#flowFrameNext').onclick=beginConfiguredPhotoSession;$('#flowExit').onclick=()=>{const configured=String(settings.exitSessionPin||'').trim();if(!configured){status.textContent='Tombol keluar terkunci. Atur PIN terlebih dahulu di Pengaturan Sesi.';alert('Atur PIN Keluar dari Sesi terlebih dahulu di menu Pengaturan Sesi.');return;}const gate=document.createElement('div');gate.className='session-pin-overlay';gate.innerHTML=`<form class="session-pin-card"><div class="eyebrow2">OPERATOR ACCESS</div><h3>Keluar dari Sesi</h3><p>Masukkan PIN operator untuk membuka kunci.</p><input type="password" inputmode="numeric" maxlength="12" autocomplete="off" placeholder="PIN operator" required><div class="actions"><button type="button" class="btn secondary" data-pin-cancel>Batal</button><button type="submit" class="btn">Buka Kunci</button></div><small class="pin-error" aria-live="polite"></small></form>`;document.body.appendChild(gate);const form=gate.querySelector('form'),input=form.querySelector('input');input.focus();gate.querySelector('[data-pin-cancel]').onclick=()=>gate.remove();gate.addEventListener('click',e=>{if(e.target===gate)gate.remove();});form.onsubmit=e=>{e.preventDefault();if(input.value!==configured){form.querySelector('.pin-error').textContent='PIN salah. Akses tetap terkunci.';input.value='';input.focus();return;}gate.remove();if(session){status.textContent='PIN benar, tetapi sesi masih aktif. Tekan “Akhiri & Pilih Foto” terlebih dahulu agar rekaman dan sesi ditutup dengan aman.';alert('PIN benar. Selesaikan atau akhiri pemotretan terlebih dahulu sebelum keluar.');return;}root.classList.remove('photo-session-content');document.body.classList.remove('photo-session-mode');go('dashboard');};};
 
 const live=$cap('#captureLive'),noVideo=$cap('#captureNoVideo'),overlay=$cap('#countOverlay'),status=$cap('#captureStatus'),start=$cap('#startSession'),take=$cap('#takePhoto'),retake=$cap('#retakePhoto'),endCapture=$cap('#endCapture'),finish=$cap('#finishSession'),gallery=$cap('#shotGallery'),counter=$cap('#shotCounter'),progress=$cap('#shotProgress'),timerEl=$cap('#sessionTimer'),liveStatus=$cap('#livePhotoStatus'),selectionControls=$cap('#selectionControls');
 let session=null,photos=[],busy=false,retakes=0,selectionMode=false,endingCapture=false,selectedNumbers=[],timerHandle=null,completionDelayHandle=null,deadline=0,recordingOK=false;
 const filterDefs=[{id:'original',name:'Original Kamera',desc:'Warna asli tanpa filter',css:'none',icon:'O'},{id:'sepia',name:'Sepia',desc:'Klasik · cokelat antik',css:'sepia(100%)',icon:'S'},{id:'chrome',name:'Chrome / Vivid',desc:'Warna tajam · kontras tinggi',css:'saturate(160%) contrast(120%) brightness(100%)',icon:'C'},{id:'vintage',name:'Vintage',desc:'Nostalgia · nuansa hangat',css:'sepia(40%) saturate(120%) contrast(90%) hue-rotate(-10deg)',icon:'V'},{id:'mono',name:'Hitam Putih',desc:'Monokrom · kontras tegas',css:'grayscale(100%) contrast(120%)',icon:'M'},{id:'cool',name:'Cool / Cinematic',desc:'Nuansa biru · sinematik',css:'hue-rotate(15deg) saturate(85%) contrast(105%)',icon:'✦'},{id:'pencil',name:'Sketsa Pensil',desc:'Arsiran pensil hitam putih',css:'none',icon:'✎'},{id:'cartoon',name:'Kartun / Ilustrasi',desc:'Warna halus dengan garis tegas',css:'none',icon:'▣'}];
 let selectedFilter=filterDefs.some(f=>f.id===settings.defaultFilter)?settings.defaultFilter:'original';
 const activeFilter=()=>filterDefs.find(f=>f.id===selectedFilter)||filterDefs[0];
 let filterPreviewRevision=0;
 const drawFilterReview=async()=>{
  const revision=++filterPreviewRevision;
  const canvas=$('#filterPreviewCanvas');if(!canvas)return;
  const ctx=canvas.getContext('2d');
  const list=selectionMode?selectedNumbers.map(n=>photos.find(p=>Number(p.number)===n)).filter(Boolean):photos.slice(0,target());
  const frameUrl=settings.frameId?`http://127.0.0.1:8765/api/frames/${settings.frameId}.png`:'';
  const loadImage=url=>new Promise(resolve=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>resolve(null);img.src=url;});
  const framePromise=frameUrl?loadImage(frameUrl):Promise.resolve(null);
  const ratioFallback=String(settings.paperSize||'4R').includes('2R')?1/3:(settings.paperSize==='Custom'?(Number(settings.customWidth||4)/Number(settings.customHeight||6)):((settings.orientation||'landscape')==='portrait'?2/3:3/2));
  const [frameImg,images]=await Promise.all([
   framePromise,
   Promise.all(list.map(photo=>loadImage((selectedFilter==='pencil'||selectedFilter==='cartoon')?`http://127.0.0.1:8765/api/session/${session.id}/filter-preview/${selectedFilter}/${encodeURIComponent(photo.original)}`:`http://127.0.0.1:8765/api/session/${session.id}/preview/${encodeURIComponent(photo.original)}`)))
  ]);
  if(revision!==filterPreviewRevision||!canvas.isConnected)return;
  const ratio=frameImg?(frameImg.naturalWidth/frameImg.naturalHeight):ratioFallback;
  const baseW=640,baseH=Math.max(1,Math.round(baseW/ratio));
  canvas.width=baseW;canvas.height=baseH;canvas.style.aspectRatio=`${baseW}/${baseH}`;
  ctx.fillStyle='#181716';ctx.fillRect(0,0,baseW,baseH);
  const slots=Array.isArray(settings.layoutSlots)&&settings.layoutSlots.length?settings.layoutSlots:list.map((_,i)=>{const cols=String(settings.paperSize||'').includes('2R')?1:(list.length>1?2:1),rows=Math.ceil(list.length/cols);return{x:(i%cols)/cols,y:Math.floor(i/cols)/rows,w:1/cols,h:1/rows};});
  const frameScale=frameImg?Math.min(baseW/frameImg.naturalWidth,baseH/frameImg.naturalHeight):1;
  const fitW=frameImg?frameImg.naturalWidth*frameScale:baseW,fitH=frameImg?frameImg.naturalHeight*frameScale:baseH,offX=(baseW-fitW)/2,offY=(baseH-fitH)/2;
  const renderSlots=slots.map((v,i)=>({x:(offX+v.x*fitW)/baseW,y:(offY+v.y*fitH)/baseH,w:v.w*fitW/baseW,h:v.h*fitH/baseH,photoIndex:Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i}));
  for(let i=0;i<renderSlots.length;i++){
   const v=renderSlots[i],im=images[Math.min(v.photoIndex,images.length-1)];if(!im)continue;
   const x=Math.round(v.x*baseW),y=Math.round(v.y*baseH),w=Math.max(1,Math.round(v.w*baseW)),h=Math.max(1,Math.round(v.h*baseH));
   ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.filter=(selectedFilter==='pencil'||selectedFilter==='cartoon')?'none':activeFilter().css; // Frame only; prevent duplicate pencil/cartoon filters.
   const scale=Math.max(w/im.naturalWidth,h/im.naturalHeight),dw=im.naturalWidth*scale,dh=im.naturalHeight*scale;
   ctx.drawImage(im,x+(w-dw)/2,y+(h-dh)/2,dw,dh);ctx.restore();
  }
  if(frameImg){const scale=Math.min(baseW/frameImg.naturalWidth,baseH/frameImg.naturalHeight),fw=frameImg.naturalWidth*scale,fh=frameImg.naturalHeight*scale;ctx.drawImage(frameImg,(baseW-fw)/2,(baseH-fh)/2,fw,fh);}
  $('#filterPreviewEmpty').hidden=!!list.length;
  const previewCanvas=$('#filterPreviewCanvas');if(previewCanvas)previewCanvas.hidden=false;
  const picker=$('#filterPhotoPicker');if(picker){picker.hidden=false;picker.innerHTML=selectionMode?`<div class="filter-photo-picker-title">PILIH FOTO UNTUK FRAME · ${selectedNumbers.length}/${target()} · tekan foto berulang untuk mengulang cetak</div><div class="filter-picked-slots">${selectedNumbers.map((n,i)=>`<button type="button" class="filter-picked-slot" data-remove-slot="${i}">SLOT ${i+1} · FOTO ${n} ×</button>`).join('')}</div><div class="filter-photo-picker-list">${photos.map(p=>`<button type="button" class="filter-photo-chip ${selectedNumbers.includes(Number(p.number))?'chosen':''}" data-pick-photo="${p.number}"><img src="http://127.0.0.1:8765/api/session/${session.id}/original/${encodeURIComponent(p.original)}" alt="Foto original ${p.number}"><span>Foto ${p.number}</span><i>${selectedNumbers.filter(n=>n===Number(p.number)).length||'+'}</i></button>`).join('')}</div>`:`<div class="filter-photo-picker-list">${photos.map(p=>`<div class="filter-photo-chip is-readonly"><img src="http://127.0.0.1:8765/api/session/${session.id}/original/${encodeURIComponent(p.original)}" alt="Foto original ${p.number}"><span>Foto ${p.number}</span></div>`).join('')}</div>`;
   picker.querySelectorAll('[data-remove-slot]').forEach(btn=>btn.onclick=()=>{selectedNumbers.splice(Number(btn.dataset.removeSlot),1);drawFilterReview();scheduleBackgroundRender();});
   picker.querySelectorAll('[data-pick-photo]').forEach(btn=>btn.onclick=()=>{const n=Number(btn.dataset.pickPhoto);if(selectedNumbers.length<target())selectedNumbers.push(n);else{$('#flowFilterNote').textContent=`Slot frame sudah penuh (${target()}). Hapus pilihan terakhir untuk mengganti.`;return;}drawFilterReview();scheduleBackgroundRender();});
   if(selectionMode&&selectedNumbers.length){picker.insertAdjacentHTML('beforeend','<button type="button" class="btn secondary small" id="removeLastPick">Hapus pilihan terakhir</button>');picker.querySelector('#removeLastPick').onclick=()=>{selectedNumbers.pop();drawFilterReview();scheduleBackgroundRender();};}
  }
  hideFlowSlideLoading();
 };
 // Siapkan hasil foto dan Live Photo ketika pelanggan masih berada di slide Filter.
 // Debounce pilihan agar klik filter/foto yang berdekatan tidak membuat render bertumpuk.
 let backgroundRenderTimer=null,backgroundRenderPromise=Promise.resolve(),backgroundRenderRevision=0,backgroundRenderRequested=false;
 const buildRenderPayload=()=>({selected_numbers:(selectionMode?selectedNumbers:photos.slice(0,target()).map(p=>Number(p.number))).slice(),frame_slots:target(),frame_id:settings.frameId||null,layout_slots:Array.isArray(settings.layoutSlots)?settings.layoutSlots.map(v=>({...v})):[],drive_qr_enabled:settings.driveQrEnabled===true,drive_qr_layout:settings.driveQrLayouts?.[settings.frameId]||settings.driveQrLayout||{x:.78,y:.78,w:.16,h:.16},filter:selectedFilter});
 const scheduleBackgroundRender=()=>{
  if(backgroundRenderTimer)clearTimeout(backgroundRenderTimer);
  if(!session||flowStep!==4)return;
  const payload=buildRenderPayload();if(!payload.selected_numbers.length)return;
  const revision=++backgroundRenderRevision;
  backgroundRenderTimer=setTimeout(()=>{
   backgroundRenderTimer=null;backgroundRenderRequested=true;
   backgroundRenderPromise=api('/api/session/prepare',{method:'POST',body:JSON.stringify(payload)}).then(()=>{
    if(revision===backgroundRenderRevision){const note=$('#flowFilterNote');if(note)note.textContent=`Filter ${activeFilter().name} dipilih. Hasil foto dan Live Photo sedang disiapkan di latar belakang.`;}
   }).catch(e=>{if(revision===backgroundRenderRevision){const note=$('#flowFilterNote');if(note)note.textContent='Pratinjau final belum dapat disiapkan: '+e.message;}});
  },450);
 };
 const waitForPreparedPreview=async()=>{
  if(backgroundRenderTimer){clearTimeout(backgroundRenderTimer);backgroundRenderTimer=null;}
  await backgroundRenderPromise.catch(()=>{});
  const payload=buildRenderPayload();if(!payload.selected_numbers.length)throw new Error('Pilih minimal satu foto untuk frame.');
  backgroundRenderRequested=true;
  await api('/api/session/prepare',{method:'POST',body:JSON.stringify(payload)});
  const started=Date.now();
  while(Date.now()-started<120000){
   const state=await api(`/api/session/${session.id}/render-status`);
   if(state.still_ready||state.render_status==='ready')return state;
   if(state.render_status==='error')throw new Error(state.render_error||'Render hasil akhir gagal.');
   const note=$('#flowFilterNote');if(note)note.textContent='Menyiapkan foto final… Live Photo dan upload Google Drive dilanjutkan di latar belakang.';
   await new Promise(resolve=>setTimeout(resolve,250));
  }
  throw new Error('Foto final belum selesai disiapkan dalam 120 detik. Periksa log backend.');
 };
 const renderFilterChoices=()=>{const box=$('#flowFilterChoices');if(!box)return;box.innerHTML=filterDefs.map(f=>`<button type="button" class="filter-choice ${f.id===selectedFilter?'selected':''}" data-filter-id="${f.id}"><span class="filter-choice-icon filter-${f.id}">${f.icon}</span><span class="filter-choice-copy"><b>${f.name}</b><small>${f.desc}</small></span><span class="filter-choice-check">✓</span></button>`).join('');box.querySelectorAll('[data-filter-id]').forEach(btn=>btn.onclick=()=>{selectedFilter=btn.dataset.filterId;settings.defaultFilter=selectedFilter;box.querySelectorAll('.filter-choice').forEach(el=>el.classList.toggle('selected',el===btn));$('#flowFilterNote').textContent=`Filter ${activeFilter().name} dipilih. Pratinjau kiri sudah diperbarui.`;drawFilterReview();scheduleBackgroundRender();});};

 renderFilterChoices();
 const target=()=>{const layout=Array.isArray(settings.layoutSlots)?settings.layoutSlots:[];if(layout.length){const used=layout.map((v,i)=>Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i);return Math.max(1,Math.min(8,Math.max(...used)+1));}return Math.max(1,Math.min(8,Number(settings.frameSlots||4)));};
 const update=()=>{mirrorToggleEl.disabled=busy;angleSwitchEl.disabled=busy||!settings.multicamEnabled||(!settings.multicamCamera2Ready&&Number(settings.activeCameraAngle||0)===0);counter.textContent=mode==='fixed_count'?`${photos.length} / ${target()} kesempatan foto`:`${photos.length} foto terkumpul`;if(mode==='fixed_count')progress.style.width=`${Math.min(100,photos.length/target()*100)}%`;take.disabled=!session||busy||selectionMode||(mode==='fixed_count'&&photos.length>=target());retake.disabled=!session||busy||photos.length===0;endCapture.disabled=!session||busy||selectionMode||mode!=='timed';finish.disabled=!session||busy||!selectionMode&&!(mode==='fixed_count'&&photos.length>=target());};
 const ensureCaptureCamera=async()=>{if(captureCameraReady)return;try{let st=await api('/api/status');if(!st.camera_open){const savedId=String(settings.cameraDeviceId||'');if(savedId.startsWith('canon_edsdk_')){st=await api('/api/canon/open',{method:'POST',body:JSON.stringify({id:savedId})});}else{const idx=Number(settings.cameraDevice??1);st=await api('/api/camera/open',{method:'POST',body:JSON.stringify({index:idx})});}}if(st.camera_open||st.ok){if(settings.multicamEnabled&&settings.multicamCamera2!==null&&settings.multicamCamera2!==undefined){try{const secondId=String(settings.multicamCamera2);if(secondId.startsWith('canon_edsdk_'))await api('/api/camera/secondary/canon/open',{method:'POST',body:JSON.stringify({id:secondId})});else await api('/api/camera/secondary/open',{method:'POST',body:JSON.stringify({index:Number(secondId)})});settings.multicamCamera2Ready=true;angleSwitchEl.disabled=false;}catch(e){settings.multicamCamera2Ready=false;angleSwitchEl.disabled=true;status.textContent='Kamera utama aktif; kamera kedua gagal dibuka: '+e.message;}}const previewRotation=Number(settings.cameraRotation??0),previewFlipX=!!settings.cameraFlipHorizontal,previewFlipY=!!settings.cameraFlipVertical,previewMirror=mirrorToggleEl.checked;live.style.transform=`scaleX(${(previewFlipX?-1:1)*(previewMirror?-1:1)}) scaleY(${previewFlipY?-1:1}) rotate(${previewRotation}deg)`;live.style.filter=`brightness(${Number(settings.livePreviewBrightness??100)}%)`;const angle=settings.multicamEnabled&&Number(settings.activeCameraAngle||0)===1&&settings.multicamCamera2Ready?1:0;await api('/api/camera/angle',{method:'POST',body:JSON.stringify({angle})}).catch(()=>{});live.src=`http://127.0.0.1:8765/${angle===1?'api/stream-secondary.mjpg':'api/stream.mjpg'}?capture=${Date.now()}&quality=${Number(settings.livePreviewQuality??76)}&fps=${Number(settings.livePreviewFps??15)}`;syncAngleSwitch();live.onload=()=>{noVideo.style.display='none';};live.onerror=()=>{noVideo.textContent='Stream kamera terputus. Periksa koneksi kamera.';};status.textContent=`Kamera aktif: index ${st.selected}, ${st.frame_width}×${st.frame_height}. Siap memulai sesi.`;}else throw new Error('Kamera belum dapat dibuka otomatis. Periksa menu Perangkat.');captureCameraReady=true;}catch(e){status.textContent='Kamera belum siap: '+e.message;throw e;}};let captureCameraReady=false;

 $cap('#mirrorButton').onclick=()=>{mirrorToggleEl.checked=!mirrorToggleEl.checked;mirrorToggleEl.dispatchEvent(new Event('change'));$cap('#mirrorButton').classList.toggle('active',mirrorToggleEl.checked);};const applyPhotoAngleOrientation=()=>{
 const secondary=Number(settings.activeCameraAngle||0)===1,suffix=secondary?'2':'';
 const rotation=Number(settings['cameraRotation'+suffix]||0);
 const flipX=!!settings['cameraFlipHorizontal'+suffix],flipY=!!settings['cameraFlipVertical'+suffix];
 const mirror=mirrorToggleEl.checked;
 // contain the image using the video stage; 90/270 uses the inverse scale.
 live.style.transform=`scaleX(${(flipX?-1:1)*(mirror?-1:1)}) scaleY(${flipY?-1:1}) rotate(${rotation}deg)`;
 live.style.objectFit='contain';
 live.style.maxWidth='100%';live.style.maxHeight='100%';
};
 mirrorToggleEl.onchange=async()=>{
 applyPhotoAngleOrientation();settings.mirrorPreview=mirrorToggleEl.checked;
 await saveScopedSettings();if(session)await api('/api/session/mirror',{method:'POST',body:JSON.stringify({mirror:settings.mirrorPreview})});
 };applyPhotoAngleOrientation();
 const countdown=async(secondsOverride)=>{const seconds=Number(secondsOverride??$cap('#shotCountdown').value);overlay.classList.add('countdown-corner');for(let n=seconds;n>0;n--){overlay.hidden=false;overlay.textContent=n;if(settings.livePhotoEnabled){try{const st=await api('/api/status');liveStatus.textContent=`Live Photo merekam · ${st.live_photo_frames||0} frame diterima · sisa ${n} detik`; }catch(e){liveStatus.textContent='Live Photo: status frame kamera tidak dapat dibaca.';}}await new Promise(r=>setTimeout(r,1000));}overlay.hidden=true;overlay.classList.remove('countdown-corner');};
 const draw=()=>{gallery.innerHTML=photos.length?photos.map((p)=>{const chosen=selectedNumbers.includes(Number(p.number));return `<div class="shot-thumb ${selectionMode&&chosen?'chosen':''} ${selectionMode?'selectable':''}" data-photo-number="${p.number}"><img loading="lazy" decoding="async" src="${p.url}" alt="Foto ${p.number}"><span>Foto ${p.number} · ${p.live_photo_url?'Live Photo tersimpan':'Live Photo tidak tersedia'}</span>${selectionMode?`<small class="selection-mark">${chosen?'✓ Dipilih':'Pilih foto'}</small>`:''}</div>`;}).join(''):'<div class="empty">Belum ada foto.</div>';if(selectionMode){gallery.querySelectorAll('[data-photo-number]').forEach(card=>card.onclick=(ev)=>{if(ev.target.closest('a,video,button'))return;const n=Number(card.dataset.photoNumber);if(selectedNumbers.length<target())selectedNumbers.push(n);else{status.textContent=`Maksimal ${target()} foto sesuai slot frame.`;return;}draw();status.textContent=`${selectedNumbers.length} dari ${target()} foto dipilih untuk frame.`;});}update();};
 const stopTimer=()=>{if(timerHandle){clearInterval(timerHandle);timerHandle=null;}if(completionDelayHandle){clearInterval(completionDelayHandle);completionDelayHandle=null;}};
 const enterSelection=async(reason)=>{if(selectionMode||endingCapture||!session)return;endingCapture=true;stopTimer();take.disabled=true;endCapture.disabled=true;status.textContent=reason||'Waktu sesi selesai. Pilih foto terbaik untuk dimasukkan ke frame.';try{await api('/api/session/stop-recording',{method:'POST',body:'{}'});}catch(e){status.textContent+=' Peringatan menghentikan rekaman: '+e.message;}selectionMode=true;endingCapture=false;selectionControls.hidden=false;finish.textContent='';selectedNumbers=[];$cap('#shotProgress').style.width='100%';liveStatus.textContent='Sesi pemotretan berhenti. Klip Live Photo per foto tersimpan jika fitur diaktifkan.';draw();};
 const tick=()=>{const remain=Math.max(0,Math.ceil((deadline-Date.now())/1000));const mm=String(Math.floor(remain/60)).padStart(2,'0'),ss=String(remain%60).padStart(2,'0');timerEl.textContent=mm+':'+ss;timerEl.hidden=false;$cap('#previewTimer').textContent=mm+':'+ss;$cap('#previewTimer').hidden=false;progress.style.width=`${Math.min(100,(1-remain/(durationMinutes*60))*100)}%`;if(remain<=0)enterSelection('Waktu '+durationMinutes+' menit telah habis. Pilih foto terbaik untuk frame.').then(()=>setFlowStep(4));};
 start.onclick=async()=>{start.dataset.lastError='';try{await ensureCaptureCamera();busy=true;update();const payload={session_mode:mode,frame_slots:target(),photo_count:target(),duration_minutes:durationMinutes,countdown:Number($cap('#shotCountdown').value),filter:selectedFilter,paper_size:settings.paperSize||'4R',print_dpi:Number(settings.printDpi||300),jpegQuality:Number(settings.jpegQuality||100),jpeg_quality:Number(settings.jpegQuality||100),video_quality:settings.videoQuality||'high',orientation:settings.orientation||'landscape',custom_width_inches:Number(settings.customWidth||4),custom_height_inches:Number(settings.customHeight||6),live_photo_enabled:!!settings.livePhotoEnabled,live_photo_duration:Number(settings.livePhotoDuration||5),frame_id:settings.frameId||null,layout_slots:Array.isArray(settings.layoutSlots)?settings.layoutSlots.map(v=>({...v})):[],drive_qr_enabled:settings.driveQrEnabled===true,drive_qr_layout:settings.driveQrLayouts?.[settings.frameId]||settings.driveQrLayout||{x:.78,y:.78,w:.16,h:.16},mirror:mirrorToggleEl.checked,camera_rotation:Number(settings.cameraRotation??0),camera_flip_horizontal:!!settings.cameraFlipHorizontal,camera_flip_vertical:!!settings.cameraFlipVertical,
 camera_rotation2:Number(settings.cameraRotation2??0),camera_flip_horizontal2:!!settings.cameraFlipHorizontal2,camera_flip_vertical2:!!settings.cameraFlipVertical2,multicam_enabled:!!settings.multicamEnabled,camera_angle:Number(settings.activeCameraAngle||0),event_id:activeEvent()?.id||null,event_name:activeEvent()?.name||'',payment_method:selectedTransactionMethod,payment_invoice:selectedTransactionMethod==='qris_doku'?paidQrisInvoice:null,voucher_code:redeemedVoucherCode||null};const r=await api('/api/session/start',{method:'POST',body:JSON.stringify(payload)});session=r.session;photos=[];selectedNumbers=[];retakes=0;selectionMode=false;endingCapture=false;selectionControls.hidden=true;finish.textContent='';recordingOK=!!settings.livePhotoEnabled;start.disabled=true;settings.defaultFilter=selectedFilter;await saveScopedSettings();liveStatus.textContent=recordingOK?'Live Photo aktif, menunggu tombol Ambil Foto. Perekaman baru dimulai setelah frame kamera terkonfirmasi.':'Live Photo nonaktif untuk sesi ini.';if(mode==='timed'){deadline=Date.now()+durationMinutes*60000;tick();timerHandle=setInterval(tick,250);status.textContent=`Sesi ${session.id} aktif selama ${durationMinutes} menit. Ambil foto sebanyak yang Anda inginkan sebelum waktu habis.`;}else{timerEl.hidden=true;$cap('#previewTimer').hidden=true;status.textContent=`Sesi ${session.id} aktif. Frame memiliki ${target()} slot, jadi tersedia ${target()} kesempatan foto.`;}}catch(e){start.dataset.lastError=e.message;status.textContent='Tidak dapat memulai sesi: '+e.message;}finally{busy=false;update();}};
 $('#flowFrameNext').disabled=!activeFrameList.length;
 take.onclick=async()=>{if(!session||busy||selectionMode)return;let liveStarted=false;try{busy=true;update();if(settings.livePhotoEnabled){status.textContent='Memulai rekaman Live Photo…';const liveSeconds=Math.max(5,Math.min(30,Number(settings.livePhotoDuration||5)));const rec=await api('/api/session/live/start',{method:'POST',body:JSON.stringify({duration_seconds:liveSeconds})});liveStarted=!!rec.recording;if(!liveStarted){const reason=rec.warning||'Perekam tidak tersedia.';liveStatus.textContent='Live Photo tidak aktif untuk foto ini: '+reason+' Foto tetap dapat diambil.';}else{liveStatus.textContent=`Live Photo ${rec.photo_number||''}: rekaman berjalan di latar belakang.`;}}status.textContent='Rekaman aktif. Countdown dimulai…';await countdown(settings.livePhotoEnabled?Number(settings.livePhotoDuration||5):undefined);status.textContent='Countdown selesai. Mengambil foto dan menutup klip Live Photo…';const r=await api('/api/session/capture',{method:'POST',body:'{}'});liveStarted=false;photos.push(r.photo);status.textContent=`Foto ${r.photo.number} berhasil disimpan (${r.photo.width}×${r.photo.height}). ${r.live_photo_created?`Klip Live Photo tersimpan (${r.live_photo_diagnostics?.frames||0} frame · ${r.live_photo_diagnostics?.duration||0} detik).`:'Foto tersimpan tanpa klip Live Photo karena frame video tidak cukup atau file tidak valid.'}`;liveStatus.textContent=r.live_photo_created?`Live Photo ${r.photo.number} tersimpan: ${r.live_photo_diagnostics?.frames||0} frame, ${r.live_photo_diagnostics?.duration||0} detik, codec ${r.live_photo_diagnostics?.codec||'-'}.` :(settings.livePhotoEnabled?'Live Photo tidak berhasil dibuat pada foto ini.':'Live Photo nonaktif.');draw();if(mode==='fixed_count'&&photos.length>=target()){selectionMode=true;selectionControls.hidden=true;selectedNumbers=photos.map(p=>Number(p.number));status.textContent='Jumlah foto sudah terpenuhi. Customer mendapat jeda sebelum berpindah ke slide berikutnya.';take.disabled=true;draw();const delay=Math.max(0,Math.min(60,Number(settings.completionDelaySeconds??10)));let remaining=delay;overlay.classList.add('countdown-corner');const finishDelay=()=>{if(completionDelayHandle){clearInterval(completionDelayHandle);completionDelayHandle=null;}overlay.hidden=true;overlay.classList.remove('countdown-corner');setFlowStep(4);status.textContent='Waktu jeda selesai. Silakan periksa foto dan pilih filter.';};if(delay<=0)finishDelay();else{overlay.hidden=false;overlay.textContent=String(remaining);completionDelayHandle=setInterval(()=>{remaining--;if(remaining<=0){finishDelay();return;}overlay.textContent=String(remaining);},1000);}}}catch(e){if(liveStarted){try{await api('/api/session/live/cancel',{method:'POST',body:'{}'});}catch{}}status.textContent='Pengambilan foto gagal: '+e.message;}finally{busy=false;update();}};
 const performRetake=async()=>{if(!session||busy||photos.length===0)return;if(backgroundRenderTimer){clearTimeout(backgroundRenderTimer);backgroundRenderTimer=null;}backgroundRenderRevision++;if(completionDelayHandle){clearInterval(completionDelayHandle);completionDelayHandle=null;}selectionMode=false;selectionControls.hidden=true;selectedNumbers=[];overlay.hidden=true;overlay.classList.remove('countdown-corner');try{busy=true;update();await backgroundRenderPromise.catch(()=>{});if(backgroundRenderRequested){for(let attempt=0;attempt<240;attempt++){const state=await api(`/api/session/${session.id}/render-status`);if(state.render_status!=='processing')break;if(attempt===239)throw new Error('Render preview masih berjalan terlalu lama.');await new Promise(resolve=>setTimeout(resolve,300));}}const r=await api('/api/session/retake',{method:'POST',body:'{}'});photos=r.photos;backgroundRenderRequested=false;retakes++;status.textContent='Foto terakhir dan Live Photo terkait dihapus. Silakan ambil ulang foto tersebut.';setFlowStep(3);draw();}catch(e){status.textContent='Gagal mengulangi foto: '+e.message;}finally{busy=false;update();}};retake.onclick=performRetake;$('#filterRetake').onclick=performRetake;
 endCapture.onclick=async()=>{await enterSelection('Sesi foto diakhiri lebih awal. Pilih foto terbaik untuk frame.');setFlowStep(4);};
 

 // v0.9.75 — loading only gates playable Live Photo. QR, JPG, local archive,
 // Drive status and upload are handled independently on the result screen.
 // Retain the off-screen video element once playback advances so WebM does not
 // restart or flash when the result screen becomes visible.
 const prepareFinalAssetsBeforeOpening=async(sid,base,requireLive)=>{
   const label=$('#flowSlideLoadingText'),progress=$('#flowFrameLoadProgress'),frameRetryButton=$('#flowFrameRetry');
   const actions=$('#flowResultLoadingActions'),retryButton=$('#flowResultRetry'),backButton=$('#flowResultDashboard'),skipButton=$('#flowResultSkip');
   if(progress)progress.hidden=true;
   if(frameRetryButton)frameRetryButton.hidden=true;
   if(actions)actions.hidden=false;
   if(retryButton)retryButton.hidden=true;
   if(backButton)backButton.hidden=true;
   // A session with Live Photo disabled has no media to wait for.
   if(!requireLive)return {video:null,videoName:'',st:null};
   showFlowSlideLoading('result');
   let skipped=false;
   // Let customers open their finished photo/QR immediately while Live Photo
   // continues rendering. Keep retry/back hidden unless preflight actually fails.
   if(actions)actions.hidden=false;
   if(retryButton)retryButton.hidden=true;
   if(backButton)backButton.hidden=true;
   if(skipButton){skipButton.hidden=false;skipButton.onclick=()=>{skipped=true;skipButton.disabled=true;setLabel('Membuka hasil foto tanpa menunggu Live Photo…');};}
   const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
   const setLabel=msg=>{if(label)label.textContent=msg;};
   const testVideo=(name)=>new Promise((resolve,reject)=>{
     const video=document.createElement('video');
     video.autoplay=true;video.muted=true;video.defaultMuted=true;video.loop=true;
     video.playsInline=true;video.preload='auto';video.controls=false;
     video.style.cssText='position:fixed;left:0;top:0;width:4px;height:4px;opacity:0.01;pointer-events:none;z-index:-1';
     root.appendChild(video);
     let ended=false,started=false;
     const cleanup=()=>{clearInterval(timer);clearTimeout(deadline);video.onloadeddata=video.oncanplay=video.onerror=null;};
     const fail=(reason)=>{if(ended)return;ended=true;cleanup();video.pause();video.removeAttribute('src');video.remove();reject(new Error(name+': '+reason));};
     const ready=()=>{if(ended)return;ended=true;cleanup();video.dataset.previewReady='1';resolve(video);};
     const tryStart=()=>{
       if(ended||started||video.readyState<2||video.videoWidth<1)return;
       started=true;
       Promise.resolve(video.play()).catch(e=>fail('pemutaran ditolak '+(e?.message||e)));
     };
     video.onloadeddata=video.oncanplay=tryStart;
     video.onerror=()=>fail('gagal decode / media error '+(video.error?.code||''));
     const timer=setInterval(()=>{
       if(skipped){fail('proses dilewati');return;}
       tryStart();
       if(started&&!video.paused&&video.currentTime>0.12&&video.readyState>=2)ready();
     },150);
     const deadline=setTimeout(()=>fail('video tidak bergerak dalam 12 detik'),12000);
     video.src=`${base}/${encodeURIComponent(name)}?preflight=${Date.now()}`;
     video.load();
   });
   const attempt=async()=>{
     const deadline=Date.now()+180000;
     let latestError='';
     // Try the playable file directly; render-status, JPG, QR and Drive must
     // never be conditions for opening the result slide.
     while(Date.now()<deadline){
       if(skipped)return {video:null,videoName:'',st:null,skipped:true};
       if(root!==$('#content')||!root.isConnected)return null;
       for(const name of ['output_live.webm','output_live.mp4']){
         if(skipped)return {video:null,videoName:'',st:null,skipped:true};
         if(root!==$('#content')||!root.isConnected)return null;
         setLabel('Menyiapkan Live Photo '+(name.endsWith('.webm')?'WebM':'MP4')+' agar langsung bergerak…');
         try{
           const video=await testVideo(name);
           if(root!==$('#content')||!root.isConnected){
             video.pause();video.removeAttribute('src');video.remove();return null;
           }
           setLabel('Live Photo siap diputar. Membuka hasil sesi…');
           return {video,videoName:name,st:null};
         }catch(err){
           if(skipped)return {video:null,videoName:'',st:null,skipped:true};
           latestError=err.message;
           console.info('[KACA_LIVE_PREFLIGHT_RETRY]',sid,latestError);
         }
       }
       setLabel('Live Photo masih dipersiapkan; mencoba kembali…');
       await pause(skipped?0:1500);
     }
     throw new Error('Live Photo belum dapat diputar setelah 3 menit. '+latestError);
   };
   while(root===$('#content')){
     if(skipped)return {video:null,videoName:'',st:null,skipped:true};
     try{
       const ready=await attempt();
       if(actions)actions.hidden=true;
       return ready;
     }catch(err){
       setLabel('Live Photo belum siap: '+err.message+' — coba lagi atau kembali ke Dashboard. File sesi tetap tersimpan.');
       if(actions)actions.hidden=false;
       if(retryButton)retryButton.hidden=false;
       if(backButton)backButton.hidden=false;
       const decision=await new Promise(resolve=>{
         retryButton.onclick=()=>resolve('retry');
         backButton.onclick=()=>resolve('dashboard');
         if(skipButton)skipButton.onclick=()=>resolve('skip');
       });
       if(actions)actions.hidden=true;
       if(decision==='skip')return {video:null,videoName:'',st:null,skipped:true};
       if(decision==='dashboard'){
         await go('dashboard');
         return null;
       }
       showFlowSlideLoading('result');
     }
   }
   return null;
 };

 finish.onclick=async()=>{let finalizedSessionId=null;try{
  /* Jangan diam-diam berhenti: tunggu proses kamera terakhir, lalu pulihkan sesi aktif dari backend bila state UI hilang. */
  if(busy){status.textContent='Menunggu proses foto terakhir selesai…';const waitUntil=Date.now()+15000;while(busy&&Date.now()<waitUntil)await new Promise(resolve=>setTimeout(resolve,100));if(busy)throw new Error('Proses foto masih sibuk setelah 15 detik. Tunggu sampai penyimpanan foto selesai, lalu coba lagi.');}
  if(!session){status.textContent='Memeriksa status sesi pemotretan…';const recovered=await api('/api/session/active');if(!recovered?.active||!recovered.session?.id)throw new Error('Sesi aktif tidak ditemukan di aplikasi maupun backend. Kembali ke Dashboard, mulai sesi baru, lalu ambil foto kembali.');session=recovered.session;photos=Array.isArray(recovered.photos)?recovered.photos:(Array.isArray(session.photos)?session.photos:[]);if(!photos.length)throw new Error('Sesi ditemukan, tetapi daftar foto kosong. Periksa kembali hasil pengambilan foto.');}
  busy=true;update();const chosen=selectionMode?selectedNumbers.slice():photos.slice(0,target()).map(p=>Number(p.number));if(!chosen.length)throw new Error('Pilih minimal satu foto untuk frame.');const r=await api('/api/session/finish',{method:'POST',body:JSON.stringify({selected_numbers:chosen,frame_slots:target(),frame_id:settings.frameId||null,layout_slots:Array.isArray(settings.layoutSlots)?settings.layoutSlots.map(v=>({...v})):[],drive_qr_enabled:settings.driveQrEnabled===true,drive_qr_layout:settings.driveQrLayouts?.[settings.frameId]||settings.driveQrLayout||{x:.78,y:.78,w:.16,h:.16},filter:selectedFilter})});/* HTTP 200 dari /finish berarti sesi sudah final. Simpan ID segera agar error UI sesudahnya tidak mengulang POST finish. */finalizedSessionId=r?.session?.id||null;if(!r?.ok||!finalizedSessionId)throw new Error('Backend belum mengembalikan konfirmasi dan ID sesi hasil.');stopTimer();session=null;selectionMode=false;endingCapture=false;selectionControls.hidden=true;$cap('#previewTimer').hidden=true;start.disabled=false;status.textContent='Sesi foto selesai. Hasil foto dan Live Photo dalam frame sedang disimpan di penyimpanan lokal.';const sid=r.session.id,base=`http://127.0.0.1:8765/api/session/${sid}`;let driveShareUrl='';$cap('#finishedResult').innerHTML=`<div class="result-card result-card-final"><div class="result-topline"><b>Hasil sesi ${sid}</b><span>Foto dan Live Photo</span></div><div class="result-workspace result-workspace-final"><section class="result-preview-column result-preview-column-final"><div class="result-preview-stage result-preview-stage-split"><section class="result-media-pane result-photo-pane"><div class="result-media-pane-inner"><img id="resultFrameImage" src="${base}/output.jpg?v=${Date.now()}" alt="Hasil foto dengan frame"></div><div class="result-media-caption">HASIL FOTO DALAM FRAME</div><div class="result-render-status notice" id="resultRenderStatus" hidden></div></section><section class="result-media-pane result-live-pane"><div class="result-media-pane-inner result-live-stage"><video id="resultLiveVideo" autoplay muted loop playsinline preload="auto" aria-label="Live Photo dalam frame" disablepictureinpicture disableremoteplayback hidden></video><img id="resultLivePlaceholder" class="result-live-placeholder" src="${base}/output.jpg?v=${Date.now()}" alt="" aria-hidden="true"><button type="button" class="result-live-retry" id="resultLiveRetry" hidden>▶ Putar Ulang Live Photo</button></div><div class="result-media-caption">LIVE PHOTO DALAM FRAME</div><div id="resultLiveStatus" class="result-live-status" aria-live="off" hidden></div></section></div></section><section class="result-files-column result-files-column-final"><section class="drive-qr-card" id="driveQrCard"><div class="drive-qr-copy"><b>SCAN QR CODE UNTUK HASIL DIGITAL</b><p id="driveQrStatus">Menyiapkan folder Google Drive dan QR Code sesi…</p><a id="driveQrOpen" class="text-link" hidden target="_blank" rel="noreferrer">Buka folder Google Drive</a></div><img id="driveQrImage" class="drive-qr-image" alt="QR Code folder Google Drive sesi" hidden></section><div class="result-share-controls"><div class="form-grid"><div class="field"><label>Nomor WhatsApp pelanggan</label><input id="customerWhatsApp" placeholder="08xxxxxxxxxx" inputmode="tel" autocomplete="tel"></div><div class="field"><label>Email pelanggan</label><input id="customerEmail" placeholder="nama@email.com" type="email"></div></div><div class="actions wrap"><button class="btn whatsapp-share" id="shareWhatsApp">Kirim WhatsApp Otomatis</button><button class="btn secondary" id="shareEmail">Share via Email</button><button class="btn secondary" id="printSession">Cetak Hasil</button></div><label class="field-help" style="display:flex;align-items:flex-start;gap:9px;margin-top:12px"><input id="whatsappConsent" type="checkbox" style="margin-top:3px"> Pelanggan menyetujui menerima tautan hasil sesi ini melalui WhatsApp.</label><div class="notice" id="shareNotice">Hasil sesi akan dikirim otomatis setelah seluruh file selesai diunggah ke Google Drive. Pastikan pelanggan menyetujui penerimaan pesan WhatsApp.</div></div></section></div><div class="result-return-bar"><div>Kembali ke Dashboard dalam <b id="resultReturnCountdown">${Math.max(5,Number(settings.resultReturnSeconds)||30)}</b> detik</div><button class="btn" id="resultFinishNow">SELESAI</button></div></div>`;
   // Slide 4 parks captureGrid in a DocumentFragment. The controls inside it are
   // invisible to document.querySelector until slide 5 moves finishedResult to root.
   // Do that BEFORE binding print/share buttons (previously a null onclick exception).
   const readyAssets=await prepareFinalAssetsBeforeOpening(sid,base,!!settings.livePhotoEnabled);
   if(!readyAssets)return true;
   setFlowStep(5);
   if(readyAssets.skipped){const live=$cap('#resultLiveStatus');if(live){live.hidden=false;live.textContent='Live Photo sedang diproses di latar belakang. Foto dan QR tetap bisa digunakan.';}}
   // Reuse only the running Live Photo. JPG and QR are loaded by their
   // existing independent result-screen handlers after the slide opens.
   // This must not depend on Drive upload, QR generation or archive status.
   if(readyAssets.video){
     const videoTarget=$cap('#resultLiveVideo');
     if(videoTarget){const vid=readyAssets.video;vid.id=videoTarget.id;vid.removeAttribute('style');vid.hidden=false;vid.controls=false;vid.dataset.previewReady='1';videoTarget.replaceWith(vid);}
     const placeholder=$cap('#resultLivePlaceholder');if(placeholder)placeholder.hidden=true;
   }
   hideFlowSlideLoading();
   let resultTimer=null,renderPoll=null;let resultLeaving=false;let liveLoadWatchdog=null;const returnToDashboard=()=>{if(liveLoadWatchdog){clearTimeout(liveLoadWatchdog);liveLoadWatchdog=null;}const live=$cap("#resultLiveVideo");if(live){try{live.pause();live.removeAttribute("src");live.load();}catch{}}if(resultLeaving)return;resultLeaving=true;if(resultTimer){clearInterval(resultTimer);resultTimer=null;}if(renderPoll){clearInterval(renderPoll);renderPoll=null;}try{stopTimer();}catch(e){console.warn('[KACA_RESULT_STOP_TIMER]',e);}photos=[];selectedNumbers=[];try{const resultNode=$cap('#finishedResult');if(resultNode)resultNode.innerHTML='';}catch(e){console.warn('[KACA_RESULT_CLEAR]',e);}api(`/api/session/${sid}/cleanup-previews`,{method:'POST',body:'{}'}).catch(e=>console.warn('[KACA_RESULT_PREVIEW_CLEANUP]',e));Promise.resolve(go('dashboard')).catch(e=>{console.error('[KACA_RESULT_DASHBOARD_NAV]',e);const resultNode=$cap('#finishedResult');if(resultNode)resultNode.innerHTML='<div class="notice">Sesi selesai. Silakan kembali ke Dashboard melalui menu navigasi.</div>';resultLeaving=false;});};const finishNowButton=$cap('#resultFinishNow');if(finishNowButton){finishNowButton.disabled=false;finishNowButton.removeAttribute('disabled');finishNowButton.style.pointerEvents='auto';finishNowButton.onclick=(ev)=>{ev.preventDefault();ev.stopPropagation();returnToDashboard();};finishNowButton.addEventListener('click',(ev)=>{ev.preventDefault();ev.stopPropagation();returnToDashboard();},{once:false});}const resultCountdownSeconds=Math.max(5,Math.min(600,Number(settings.resultReturnSeconds)||30));let resultCountdownStarted=false,resultDeadline=0,resultStatusSnapshot=null;const resultCountdownEl=$cap('#resultReturnCountdown');if(resultCountdownEl){resultCountdownEl.textContent=String(resultCountdownSeconds);resultCountdownEl.setAttribute('aria-live','off');}const updateResultCountdown=()=>{if(resultLeaving||!resultCountdownStarted)return;const left=Math.max(0,Math.ceil((resultDeadline-Date.now())/1000));const el=$cap('#resultReturnCountdown');if(el)el.textContent=String(left);if(left<=0)returnToDashboard();};const maybeStartResultCountdown=()=>{if(resultLeaving||resultCountdownStarted)return;/* Countdown slide akhir mulai tepat ketika slide dibuka; kesiapan QR, render lokal, dan upload tidak boleh menahannya. */resultCountdownStarted=true;resultDeadline=Date.now()+resultCountdownSeconds*1000;updateResultCountdown();resultTimer=setInterval(updateResultCountdown,250);};let resultAutoPrintSent=false,resultAutoPrintBusy=false,resultAutoPrintAttempts=0;
 const makePrintRequest=async(copies,automatic=false)=>{
   const input={printer_name:settings.printerName||'',paper_size:settings.paperSize||'4R',
      custom_width:Number(settings.customWidth||4),custom_height:Number(settings.customHeight||6),
      copies:Math.max(1,Math.min(20,Number(copies)||1)),dpi:Number(settings.printDpi||300),
      borderless:!!settings.printBorderless,driver_paper_name:settings.printerDriverPaper||'',
      auto_print:!!automatic};
   return api(`/api/session/${sid}/print`,{method:'POST',body:JSON.stringify(input)});
 };
 const printButton=$cap('#printSession');
 if(settings.autoPrintEnabled){printButton.disabled=true;printButton.textContent='Cetak Otomatis Aktif';}
 else if(settings.additionalPrintEnabled)printButton.textContent='Tambah Cetak';
 printButton.onclick=async()=>{
   if(settings.autoPrintEnabled)return;
   const btn=$cap('#printSession'),notice=$cap('#shareNotice');
   let copies=Number(settings.printCopies||1);
   if(settings.additionalPrintEnabled){
     const max=Math.max(1,Math.min(20,Number(settings.additionalPrintMaxCopies||5)));
     copies=await new Promise(resolve=>{
       const overlay=document.createElement('div');overlay.className='session-pin-overlay';
       overlay.innerHTML=`<div class="session-pin-card"><h3>Tambah Cetak Hasil</h3><p>Pilih jumlah salinan yang ingin dicetak.</p><select id="customerPrintCopies">${Array.from({length:max},(_,i)=>`<option value="${i+1}">${i+1} lembar</option>`).join('')}</select><div class="actions"><button type="button" class="btn" data-print-confirm>Cetak Sekarang</button><button type="button" class="btn secondary" data-print-cancel>Batal</button></div></div>`;
       document.body.appendChild(overlay);
       overlay.querySelector('[data-print-confirm]').onclick=()=>{const value=Number(overlay.querySelector('#customerPrintCopies').value);overlay.remove();resolve(value);};
       overlay.querySelector('[data-print-cancel]').onclick=()=>{overlay.remove();resolve(null);};
     });
     if(copies==null)return;
   }
   try{btn.disabled=true;btn.textContent='Mengirim ke printer…';const pr=await makePrintRequest(copies);
     notice.textContent=pr.message||`${copies} salinan dikirim ke antrean printer.`;
   }catch(e){notice.textContent='Gagal mencetak: '+e.message;}
   finally{btn.disabled=false;btn.textContent=settings.additionalPrintEnabled?'Tambah Cetak':'Cetak Hasil';}
 };
 const maybeStartAutoPrint=async(st)=>{
   if(!settings.autoPrintEnabled||resultAutoPrintSent||resultAutoPrintBusy||resultLeaving)return;
   if(!st.still_ready|| (settings.driveQrEnabled&& !st.drive_url))return;
   if(resultAutoPrintAttempts>=12)return;
   resultAutoPrintBusy=true;resultAutoPrintAttempts++;
   const notice=$cap('#shareNotice');
   try{
     const pr=await makePrintRequest(settings.printCopies||1,true);
     resultAutoPrintSent=true;
     if(notice)notice.textContent=pr.message||'Cetak otomatis telah dikirim ke printer.';
     if(printButton){printButton.disabled=true;printButton.textContent='Sudah Dicetak Otomatis ✓';}
   }catch(e){
     if(notice)notice.textContent='Cetak otomatis: '+e.message;
     // Retry while render/QR folder is pending. For permanent printer errors
     // stop polling instead of queuing repeated requests.
     if(!/belum|siap|menunggu|render|QR/i.test(e.message))resultAutoPrintAttempts=12;
   }finally{resultAutoPrintBusy=false;}
 };
 let activeWhatsAppJob=null,whatsappPoll=null;
 $('#shareWhatsApp').textContent=settings.waDeliveryMode==='click_to_chat'?'Buka WhatsApp untuk Mengirim':settings.waDeliveryMode==='gateway_fonnte'?'Kirim Link WhatsApp':'Kirim WhatsApp Otomatis';$('#shareNotice').textContent=settings.waDeliveryMode==='click_to_chat'?'WhatsApp akan terbuka dengan pesan dan tautan Google Drive yang sudah disiapkan. Operator menekan Kirim di WhatsApp.':'Pesan WhatsApp akan dikirim melalui Cloud API setelah file hasil utama tersedia dan tautan Google Drive siap.';$('#shareWhatsApp').onclick=async()=>{const btn=$('#shareWhatsApp'),notice=$('#shareNotice'),phone=$('#customerWhatsApp').value.trim();if(!phone){notice.textContent='Masukkan nomor WhatsApp pelanggan terlebih dahulu.';$('#customerWhatsApp').focus();return;}if(!$('#whatsappConsent').checked){notice.textContent='Minta persetujuan pelanggan sebelum mengirim hasil melalui WhatsApp.';return;}if(settings.waDeliveryMode==='gateway_fonnte'){
 if(!driveShareUrl){notice.textContent='Tautan Google Drive belum tersedia. Coba beberapa saat lagi.';return;}
 try{btn.disabled=true;btn.textContent='Mengirim lewat gateway…';const response=await api('/api/whatsapp/fonnte/send',{method:'POST',body:JSON.stringify({session_id:sid,phone,consent:true})});notice.textContent=response.duplicate?'Permintaan pesan untuk nomor ini sudah pernah diterima gateway.':'Gateway menerima permintaan pengiriman. Status diterima pelanggan belum dapat dipastikan.';btn.textContent='Permintaan Terkirim ✓';}
 catch(e){notice.textContent='Gagal mengirim melalui gateway: '+e.message;btn.disabled=false;btn.textContent='Coba Kirim Lagi';}return;
 }if(settings.waDeliveryMode==='click_to_chat'){if(!driveShareUrl){notice.textContent='Tautan Google Drive belum tersedia. Tunggu sampai folder sesi berhasil dibuat, lalu coba lagi.';return;}const digits=phone.replace(/\D/g,'');const normalized=digits.startsWith('0')?'62'+digits.slice(1):digits.startsWith('8')?'62'+digits:digits;if(normalized.length<10||normalized.length>15){notice.textContent='Nomor WhatsApp tidak valid. Gunakan format Indonesia, misalnya 081234567890.';return;}const message='Halo! Terima kasih telah menggunakan layanan KACA STUDIO.\n\nHasil foto sesi Anda sudah tersedia. Silakan buka tautan berikut untuk melihat dan mengunduh foto: '+driveShareUrl+'\n\nTerima kasih!';const waUrl='https://wa.me/'+normalized+'?text='+encodeURIComponent(message);try{await window.kaca.openExternal(waUrl);notice.textContent='WhatsApp dibuka dengan pesan dan tautan Google Drive yang sudah terisi. Periksa pesan, lalu tekan Kirim di WhatsApp.';}catch(e){notice.textContent='Tidak dapat membuka WhatsApp: '+e.message;}return;}try{btn.disabled=true;btn.textContent='Memasukkan antrean…';const r=await api('/api/whatsapp/send',{method:'POST',body:JSON.stringify({session_id:sid,phone,consent:true})});activeWhatsAppJob=r.job.id;notice.textContent=r.duplicate?'Pengiriman untuk nomor ini sudah pernah dimasukkan. Memeriksa status…':'Antrean WhatsApp dibuat. Menunggu file hasil utama tersedia di Google Drive…';if(whatsappPoll)clearInterval(whatsappPoll);const check=async()=>{try{const st=await api('/api/whatsapp/job/'+activeWhatsAppJob);const j=st.job;if(!j)return;if(j.status==='sent'){notice.textContent='Pesan WhatsApp berhasil diterima API Meta untuk dikirim. ID: '+j.message_id;btn.textContent='Terkirim ✓';btn.disabled=true;clearInterval(whatsappPoll);}else if(j.status==='waiting_drive'||j.status==='pending'){notice.textContent='Menunggu upload Google Drive selesai…';btn.textContent='Menunggu Drive…';btn.disabled=true;}else if(j.status==='sending'){notice.textContent='Sedang mengirim melalui WhatsApp Cloud API…';btn.textContent='Mengirim…';btn.disabled=true;}else if(j.status==='error'){notice.textContent='Pengiriman gagal: '+(j.error||'kesalahan tidak diketahui')+'. Tekan tombol Coba Lagi di bawah untuk mengulang.';btn.textContent='Coba Kirim Lagi';btn.disabled=false;btn.onclick=async()=>{try{const rr=await api('/api/whatsapp/retry',{method:'POST',body:JSON.stringify({job_id:activeWhatsAppJob})});if(rr.already_sent){notice.textContent='Pesan ini sudah terkirim sebelumnya.';btn.disabled=true;return;}btn.onclick=null;btn.textContent='Menunggu…';btn.disabled=true;whatsappPoll=setInterval(check,2500);}catch(e){notice.textContent='Gagal mengulang: '+e.message;}};clearInterval(whatsappPoll);}}catch(e){notice.textContent='Tidak dapat memeriksa status WhatsApp: '+e.message;}};await check();if(!['sent','error'].includes((await api('/api/whatsapp/job/'+activeWhatsAppJob)).job?.status))whatsappPoll=setInterval(check,2500);}catch(e){notice.textContent='Tidak dapat membuat pengiriman WhatsApp: '+e.message;btn.disabled=false;btn.textContent='Kirim WhatsApp Otomatis';}};$('#shareEmail').onclick=()=>{const email=$('#customerEmail').value.trim();if(!email||!email.includes('@')){$('#shareNotice').textContent='Masukkan alamat email pelanggan yang valid.';return;}const mailto=`mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent('Hasil Foto KACA.ID - '+sid)}&body=${encodeURIComponent('Hasil foto sesi '+sid+' sudah siap. '+(driveShareUrl?'Tautan Google Drive: '+driveShareUrl:'Tautan Google Drive akan dikirim setelah upload selesai.'))}`;window.kaca.openExternal(mailto).then(()=>{$('#shareNotice').textContent='Aplikasi email dibuka dengan alamat dan pesan hasil sesi.';}).catch(e=>{$('#shareNotice').textContent='Tidak dapat membuka aplikasi email: '+e.message;});};// v0.9.72: preview hasil sesi hanya menggunakan video WebM, kemudian MP4.
// JPG hanya digunakan sebagai placeholder statis bila video belum siap/gagal.
// Tidak ada fallback GIF untuk slide hasil akhir.
let liveStarted=!!readyAssets.video,liveFinished=!!readyAssets.video,liveVideoStage=0,liveVideoCandidates=[],liveAttemptToken=0;
const liveNotice=msg=>{const el=$cap('#resultLiveStatus');if(el)el.textContent=msg;console.info('[KACA_LIVE_RESULT]',sid,msg);};
const liveRetry=$cap('#resultLiveRetry');
const liveVid=$cap('#resultLiveVideo');
const livePlaceholder=$cap('#resultLivePlaceholder');
const showLiveMedia=kind=>{
  if(resultLeaving)return;
  const videoReady=kind==='video';
  if(liveVid)liveVid.hidden=!videoReady;
  if(livePlaceholder)livePlaceholder.hidden=videoReady;
  if(liveRetry)liveRetry.hidden=true;
  if(videoReady){
    liveFinished=true;
    hideFlowSlideLoading();
    if(resultCountdownStarted&&liveVid&&!liveVid.dataset.countdownExtended){
      liveVid.dataset.countdownExtended='1';
      resultDeadline=Math.max(resultDeadline,Date.now()+Math.min(20,resultCountdownSeconds)*1000);
      updateResultCountdown();
    }
  }
};
const displayLiveFailure=msg=>{
  if(liveVid){liveVid.hidden=true;liveVid.dataset.previewReady='';}
  if(livePlaceholder)livePlaceholder.hidden=false;
  liveNotice(msg);
  console.warn('[KACA_RESULT_VIDEO_UNAVAILABLE]',{session:sid,message:msg,videoError:liveVid?.error?.code||null});
  // The retry button is hidden from customers by the existing result CSS.
  if(liveRetry)liveRetry.hidden=false;
};
const tryVideoCandidate=()=>{
  if(resultLeaving||liveFinished||!liveVid)return;
  if(liveLoadWatchdog){clearTimeout(liveLoadWatchdog);liveLoadWatchdog=null;}
  if(liveVideoStage>=liveVideoCandidates.length){
    displayLiveFailure('Live Photo WebM dan MP4 belum dapat diputar. Foto hasil tetap tersedia.');
    return;
  }
  const name=liveVideoCandidates[liveVideoStage++];
  const token=++liveAttemptToken;
  let playRequested=false,failed=false;
  liveVid.dataset.previewReady='';
  liveNotice('Memuat Live Photo '+name+'…');
  const failVideo=reason=>{
    if(resultLeaving||token!==liveAttemptToken||failed)return;
    failed=true;
    liveFinished=false;
    if(liveLoadWatchdog){clearTimeout(liveLoadWatchdog);liveLoadWatchdog=null;}
    console.warn('[KACA_RESULT_VIDEO_FALLBACK]',{sid,name,reason,error:liveVid.error?.code||null,network:liveVid.networkState,ready:liveVid.readyState});
    try{liveVid.pause();liveVid.removeAttribute('src');liveVid.load();}catch{}
    liveVid.dataset.previewReady='';
    showLiveMedia('still');
    tryVideoCandidate();
  };
  const startPlayback=()=>{
    if(resultLeaving||token!==liveAttemptToken||failed||playRequested)return;
    if(liveVid.readyState<2||liveVid.videoWidth<1)return;
    playRequested=true;
    // Unhide before play() so Electron will actually render video frames.
    liveVid.hidden=false;
    if(livePlaceholder)livePlaceholder.hidden=true;
    liveVid.muted=true;
    liveVid.defaultMuted=true;
    liveVid.playsInline=true;
    liveVid.loop=true;
    liveVid.controls=false;
    let playResult;
    try{playResult=liveVid.play();}catch(err){failVideo('play() threw '+(err?.message||err));return;}
    Promise.resolve(playResult).then(()=>{
      if(resultLeaving||token!==liveAttemptToken||failed)return;
      if(liveLoadWatchdog){clearTimeout(liveLoadWatchdog);liveLoadWatchdog=null;}
      liveVid.dataset.previewReady='1';
      showLiveMedia('video');
      liveNotice('Live Photo '+name+' sedang diputar otomatis.');
    }).catch(err=>failVideo('play() rejected '+(err?.name||'unknown')));
  };
  liveVid.onloadeddata=startPlayback;
  liveVid.oncanplay=startPlayback;
  liveVid.onplaying=startPlayback;
  liveVid.onerror=()=>failVideo('media error '+(liveVid.error?.code||'-'));
  liveVid.onabort=()=>failVideo('media aborted');
  liveVid.onstalled=()=>liveNotice('Menunggu buffer video '+name+'…');
  liveVid.onwaiting=()=>liveNotice('Buffering video '+name+'…');
  liveVid.src=`${base}/${encodeURIComponent(name)}?live=${Date.now()}&try=${token}`;
  liveVid.preload='auto';
  liveVid.load();
  liveLoadWatchdog=setTimeout(()=>{
    if(resultLeaving||token!==liveAttemptToken||failed)return;
    if(!playRequested&&liveVid.readyState>=2&&liveVid.videoWidth>0)startPlayback();
    else failVideo('playback timeout 9 detik');
  },9000);
};
const prepareLivePreview=st=>{
  if(liveStarted||resultLeaving||liveFinished)return;
  // WebM is always first regardless of backend manifest order.
  liveVideoCandidates=['output_live.webm','output_live.mp4'];
  liveStarted=true;
  tryVideoCandidate();
};
if(liveRetry)liveRetry.onclick=()=>{
  liveFinished=false;liveStarted=true;liveVideoStage=0;
  if(liveVid){liveVid.dataset.previewReady='';liveVid.hidden=true;}
  if(livePlaceholder)livePlaceholder.hidden=false;
  liveRetry.hidden=true;
  tryVideoCandidate();
};
if(liveVid){liveVid.controls=false;liveVid.style.pointerEvents='none';liveVid.setAttribute('tabindex','-1');}
let renderPollBusy=false;const pollResultStatus=async()=>{if(renderPollBusy)return;renderPollBusy=true;try{const st=await api(`/api/session/${sid}/render-status`);resultStatusSnapshot=st;void maybeStartAutoPrint(st);const qrStatus=$cap('#driveQrStatus'),qrImage=$cap('#driveQrImage'),qrOpen=$cap('#driveQrOpen');if(st.drive_url)driveShareUrl=st.drive_url;
// Always request the local QR endpoint, even when Drive status/manifest flags are stale.
// This mirrors v0.9.44's working endpoint flow while allowing an archive-path fallback.
if(qrImage&&!qrImage.dataset.qrLoaded){if(!qrImage.dataset.qrRequest||qrImage.dataset.qrRequestAt<Date.now()-2500){qrImage.dataset.qrRequest='1';qrImage.dataset.qrRequestAt=String(Date.now());qrImage.onload=()=>{qrImage.hidden=false;qrImage.dataset.qrLoaded='1';qrImage.dataset.qrFailed='';hideFlowSlideLoading();maybeStartResultCountdown();
 if(resultCountdownStarted&&!qrImage.dataset.qrScanDeadlineExtended){
  qrImage.dataset.qrScanDeadlineExtended='1';
  resultDeadline=Math.max(resultDeadline,Date.now()+resultCountdownSeconds*1000);
  updateResultCountdown();
 }if(qrStatus)qrStatus.textContent=st.drive_url?'QR Code siap dipindai. File sesi sedang disinkronkan ke Google Drive.':'QR lokal berhasil dimuat.';};qrImage.onerror=async()=>{qrImage.hidden=true;qrImage.dataset.qrLoaded='';qrImage.dataset.qrFailed='1';hideFlowSlideLoading();maybeStartResultCountdown();try{const response=await fetch(`${base}/qr.png?diagnostic=${Date.now()}`,{cache:'no-store'});let detail='QR belum tersedia pada backend.';if(!response.ok){try{const body=await response.json();detail=body.error||detail;}catch{detail=`HTTP ${response.status}`;}}if(qrStatus)qrStatus.textContent=detail;}catch(err){if(qrStatus)qrStatus.textContent='Tidak dapat memuat QR lokal: '+err.message;}};qrImage.src=`${base}/qr.png?local=${Date.now()}`;qrImage.hidden=false;}}
if(qrOpen){qrOpen.hidden=!st.drive_url;if(st.drive_url)qrOpen.href=st.drive_url;}
if(qrStatus&&!qrImage?.dataset.qrLoaded&&!st.drive_url){qrStatus.textContent=st.drive_folder_status==='creating'?'Sedang membuat folder Google Drive; QR lokal sedang diperiksa…':st.drive_folder_status==='waiting_auth'?'QR lokal sedang diperiksa. Hubungkan Google Drive untuk membuat tautan yang dapat dipindai.':(st.drive_qr_error||st.drive_error||'Memeriksa QR lokal sesi…');}
const statusEl=$cap('#resultRenderStatus');if(st.render_status==='error'){if(statusEl)statusEl.textContent='Render hasil foto/Live Photo gagal: '+(st.render_error||'kesalahan tidak diketahui');}else{if(st.local_archive_status==='error'){if(statusEl)statusEl.textContent='Preview siap, tetapi penyimpanan arsip lokal gagal: '+(st.local_archive_error||'periksa izin folder penyimpanan');}else if(st.local_archive_status==='ready'){if(st.drive_status==='ready'&&st.drive_url){if(statusEl)statusEl.textContent='Hasil tersimpan lokal dan Google Drive.';}else if(statusEl)statusEl.textContent='Hasil tersimpan di lokal. Upload Google Drive berjalan di latar belakang.';}else if(statusEl)statusEl.textContent='Memproses dan menyimpan hasil sesi…';}
const img=$cap('#resultFrameImage');if(img&&st.still_ready&&!img.dataset.resultLoaded){img.onload=()=>hideFlowSlideLoading();img.onerror=()=>hideFlowSlideLoading();img.src=`${base}/output.jpg?v=${Date.now()}`;img.dataset.resultLoaded='1';}
const livePlaceholderImage=$cap('#resultLivePlaceholder');if(livePlaceholderImage&&st.still_ready&&!livePlaceholderImage.dataset.resultLoaded){livePlaceholderImage.src=`${base}/output.jpg?v=${Date.now()}`;livePlaceholderImage.dataset.resultLoaded='1';}
// v0.9.66: media-state orchestration, independent of QR/Drive and backend flags.
if(st.live_photo_enabled && (st.live_output_available || st.live_output_preview_available || st.live_output)){
  prepareLivePreview(st);
}else if(st.render_status==='ready'&&!st.live_photo_enabled){
  const liveNote=$cap('#resultLiveStatus');if(liveNote)liveNote.textContent='Live Photo tidak diaktifkan untuk sesi ini.';
}else if(st.render_status==='ready'&&!liveStarted){
  const liveNote=$cap('#resultLiveStatus');if(liveNote)liveNote.textContent='Klip Live Photo belum tersedia; hasil JPG tetap tersimpan.';
}
maybeStartResultCountdown();if(st.render_status==='ready'&&st.local_archive_status==='ready'&&(st.drive_status==='ready'||st.drive_status==='local_only'||st.drive_status==='waiting_auth'||st.drive_status==='uploading'||st.drive_status==='pending')){if(st.drive_status==='ready'||st.drive_status==='local_only'){
  const qrLoaded=Boolean($cap('#driveQrImage')?.dataset.qrLoaded);
  const videoRequired=Boolean(st.live_photo_enabled&&(st.live_output_preview_available||st.live_output_available));
  const videoLoaded=Boolean($cap('#resultLiveVideo')?.dataset.previewReady);
  if(qrLoaded&&(!videoRequired||videoLoaded)){clearInterval(renderPoll);renderPoll=null;}
 }}
}catch(e){const note=$cap('#resultRenderStatus');if(note)note.textContent='Menghubungkan kembali ke status hasil… '+e.message;const qrNote=$cap('#driveQrStatus');if(qrNote)qrNote.textContent='Memeriksa kembali QR lokal: '+e.message;console.warn('[KACA_RESULT_STATUS_POLL]',e);}finally{renderPollBusy=false;}};renderPoll=setInterval(pollResultStatus,1500);pollResultStatus();maybeStartResultCountdown();return true;}catch(e){if(finalizedSessionId){/* Hanya ID yang diterima dari respons finish yang membuktikan sesi sudah difinalisasi. */const sid=finalizedSessionId;status.textContent='Sesi berhasil difinalisasi. Tampilan hasil mengalami kendala saat dimuat.';try{if(sid){const base=`http://127.0.0.1:8765/api/session/${sid}`;const result=$cap('#finishedResult');if(result&&!result.innerHTML.trim())result.innerHTML=`<div class="result-card"><h3>Hasil sesi ${sid}</h3><p>Foto Anda sudah difinalisasi dan sedang diproses.</p><img src="${base}/output.jpg?v=${Date.now()}" alt="Hasil foto" style="display:block;max-width:100%;height:auto"><p id="resultFallbackStatus">Memuat hasil sesi…</p><button type="button" class="btn secondary" id="resultFallbackReturn">KEMBALI KE DASHBOARD</button></div>`;const back=$cap('#resultFallbackReturn');if(back)back.onclick=()=>{result.innerHTML='';photos=[];selectedNumbers=[];go('dashboard');};}setFlowStep(5);const note=$cap('#flowFilterNote');if(note)note.textContent='Sesi sudah tersimpan. Tampilan hasil sedang dipulihkan; jangan ulangi finalisasi.';}catch(fallbackError){console.error('[CUSTOMER_RESULT_UI_ERROR]',fallbackError);try{setFlowStep(5);}catch{}}return true;}status.textContent='Gagal menyelesaikan sesi: '+e.message;throw e;}finally{busy=false;update();}};
 $cap('#flowCaptureStart').hidden=true;
 $('#flowFilterNext').onclick=async()=>{if(mode==='timed'&&!selectionMode){await enterSelection('Pilih foto terbaik untuk hasil akhir.');setFlowStep(4);return;}if(!photos.length){status.textContent='Belum ada foto dalam sesi.';return;}const btn=$('#flowFilterNext');try{btn.disabled=true;btn.textContent='MENYIMPAN HASIL…';const note=$('#flowFilterNote');if(note)note.textContent='Menyelesaikan sesi. Live Photo akan disiapkan sebelum hasil ditampilkan; QR dan upload berjalan terpisah.';/* Jangan menunggu render preview 120 detik di layar pelanggan. Endpoint finish mengantrekan render final dan segera mengembalikan session ID. */if(settings.livePhotoEnabled)showFlowSlideLoading('result');const finished=await finish.onclick();if(finished!==true)throw new Error(status.textContent||'Backend belum mengonfirmasi finalisasi sesi.');}catch(e){hideFlowSlideLoading();const note=$('#flowFilterNote');if(note)note.textContent='Finalisasi belum berhasil: '+e.message;status.textContent='Finalisasi belum berhasil: '+e.message;console.error('[KACA_FILTER_FINALIZE_BLOCKED]',e);btn.textContent='COBA LAGI';}finally{if(root===$('#content')){btn.disabled=false;if(btn.textContent!=='COBA LAGI')btn.textContent='LANJUT KE HASIL';}}};
 const voucherEnabled=settings.enableVoucherPayment!==false,qrisEnabled=settings.enableQrisPayment!==false;const transactionEnabled=voucherEnabled||qrisEnabled;
 const transactionStep=root.querySelector('[data-step-label="1"]');
 root.classList.toggle('skip-transaction',!transactionEnabled);
 if(transactionStep)transactionStep.hidden=!transactionEnabled;
 transactionPanel.hidden=true;
 captureUiReady=true;
 transactionPanel.querySelectorAll('[data-transaction-method]').forEach(btn=>{btn.disabled=btn.hidden;btn.removeAttribute('aria-disabled');});
 const enterPreparedStartFlow=async()=>{
   if(frameLoadRunning||root!==$('#content'))return;
   frameLoadRunning=true;showFlowSlideLoading(0);
   if(frameRetry)frameRetry.hidden=true;
   updateFrameLoading(frameLoadedCount,activeFrameList.length);
   try{
     const result=await preloadAllFrames();
     if(root!==$('#content'))return;
     if(!result.ok){
       frameReadyPromise=null;framePreloadedSuccessfully=false;
       if(frameLoadingLabel)frameLoadingLabel.textContent=`${result.missing.length} frame tidak dapat dimuat. Periksa backend, lalu coba lagi.`;
       if(frameRetry)frameRetry.hidden=false;
       return;
     }
     framePreloadedSuccessfully=true;
     if(transactionEnabled){setFlowStep(1);transactionPanel.hidden=false;}
     else{setFlowStep(2);}
     hideFlowSlideLoading();
     if(frameProgress)frameProgress.hidden=true;
     const notice=$('#flowFrameStatus');
     if(notice)notice.textContent=`${activeFrameList.length} frame siap dipilih.`;
   }catch(err){
     frameReadyPromise=null;framePreloadedSuccessfully=false;
     if(frameLoadingLabel)frameLoadingLabel.textContent='Gagal menyiapkan alur sesi: '+err.message;
     if(frameRetry)frameRetry.hidden=false;
   }finally{frameLoadRunning=false;}
 };
 if(flowFrames.loadError){
   showFlowSlideLoading(0);
   if(frameLoadingLabel)frameLoadingLabel.textContent='Gagal membaca daftar frame dari backend: '+flowFrames.loadError;
   if(frameRetry){frameRetry.hidden=false;frameRetry.textContent='Coba Hubungkan & Muat Ulang';frameRetry.onclick=()=>{frameRetry.hidden=true;void renderCapture();};}
 }else{
   if(frameRetry)frameRetry.onclick=enterPreparedStartFlow;
   void enterPreparedStartFlow();
 }
 update();
}

async function renderFrames(){
 const pageGeneration=navigationGeneration;
 const current=settings.paperSize||'4R';let frameList=[],selectedFrame=settings.frameId||'';let frameLayouts=settings.frameLayouts&&typeof settings.frameLayouts==='object'?settings.frameLayouts:{};const initialSlots=Array.isArray(frameLayouts[selectedFrame])&&frameLayouts[selectedFrame].length?frameLayouts[selectedFrame]:settings.layoutSlots;let slots=Array.isArray(initialSlots)?JSON.parse(JSON.stringify(initialSlots)).map((v,i)=>({x:Number(v.x)*100,y:Number(v.y)*100,w:Number(v.w)*100,h:Number(v.h)*100,photo_index:Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i})):[];let qrEnabled=settings.driveQrEnabled===true;const qrDefaults={x:78,y:78,w:16,h:16};const loadQrLayout=(id)=>{const raw=settings.driveQrLayouts?.[id]||settings.driveQrLayout;if(!raw)return {...qrDefaults};return {x:Number(raw.x)*100,y:Number(raw.y)*100,w:Number(raw.w)*100,h:Number(raw.h)*100};};let qrLayout=loadQrLayout(selectedFrame);
 const fresh=()=>Array.from({length:Number(settings.frameSlots||4)},(_,i)=>({x:(i%2)*50+5,y:Math.floor(i/2)*45+8,w:40,h:38,photo_index:i}));
 if(!slots.length)slots=fresh();
 const frames=await api('/api/frames');if(pageGeneration!==navigationGeneration)return;frameList=(frames.frames||[]).filter(frameBelongsToCurrentEvent);
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / FRAME & LAYOUT EDITOR</div><h3>Frame PNG & Penempatan Foto</h3><p class="muted">Impor PNG transparan dari komputer. Area transparan pada PNG akan menampilkan foto; bagian desain/ornamen tetap berada di lapisan atas. Operator dapat menambah, menghapus, mengatur jumlah, serta mengubah posisi dan ukuran slot secara manual.</p><h3>Frame Tersimpan</h3><div class="frame-management-grid">${frameList.map(f=>`<article class="frame-management-card"><img src="${f.url}" alt="${f.name}"><b>${f.name}</b><small>${f.width||'—'} × ${f.height||'—'} px</small><label class="frame-enable-check"><input type="checkbox" data-frame-enabled="${f.id}" ${f.enabled!==false && f.active!==false?'checked':''}><span>Tampilkan dalam pilihan sesi foto</span></label><div class="actions wrap"><button class="btn secondary small" data-frame-edit="${f.id}">Edit</button><button class="btn secondary small" data-frame-delete="${f.id}">Hapus</button></div></article>`).join('')||'<div class="empty">Belum ada frame tersimpan.</div>'}</div>
 <div class="form-grid"><div class="field"><label>Impor frame PNG transparan</label><input id="frameFile" type="file" accept="image/png"><small class="field-help">PNG maksimal 15 MB dan harus memiliki kanal transparansi (alpha).</small></div><div class="field"><label>Frame tersimpan</label><select id="savedFrames"><option value="">Tanpa frame PNG / layout kosong</option>${frameList.map(f=>`<option value="${f.id}" ${selectedFrame===f.id?'selected':''}>${f.name||f.id}</option>`).join('')}</select></div><div class="field"><label>Ukuran output</label><select id="layoutSize">${['4R','2R Strip','Custom'].map(x=>`<option ${current===x?'selected':''}>${x}</option>`).join('')}</select></div><div class="field"><label>Orientasi</label><select id="layoutOrientation"><option value="landscape" ${(settings.orientation||'landscape')==='landscape'?'selected':''}>Landscape</option><option value="portrait" ${settings.orientation==='portrait'?'selected':''}>Portrait</option></select></div><div class="field custom-size-field" id="customSizeFields"><label>Lebar custom (inci)</label><input id="customWidth" type="number" min="1" max="20" step="0.1" value="${settings.customWidth||4}"></div><div class="field custom-size-field"><label>Tinggi custom (inci)</label><input id="customHeight" type="number" min="1" max="20" step="0.1" value="${settings.customHeight||6}"></div></div>
 <div class="panel" style="margin-top:14px"><h3>Buat Frame PNG dari Awal</h3><p class="muted">Buat desain dasar dengan warna, judul, dan footer. Aplikasi akan membuat lubang transparan sesuai posisi slot foto di bawah.</p><div class="form-grid"><div class="field"><label>Warna dasar frame</label><input id="frameBgColor" type="color" value="#171717"></div><div class="field"><label>Warna aksen / garis</label><input id="frameAccentColor" type="color" value="#d8b56a"></div><div class="field"><label>Judul frame</label><input id="frameTitle" value="KACA.ID"></div><div class="field"><label>Teks bawah</label><input id="frameFooter" value="SAY CHEESE, SAY KACA"></div></div><button class="btn secondary" id="createFramePng">Buat & Simpan Frame PNG</button></div>
 <div class="actions wrap"><button class="btn secondary" id="addSlot">+ Tambah Slot Foto</button><button class="btn secondary" id="duplicateSlot">Duplikasi Slot Terakhir (Foto Sama)</button><button class="btn secondary" id="removeSlot">− Hapus Slot Terakhir</button><button class="btn secondary" id="resetSlots">Susun Otomatis</button></div>
 <div class="field" style="max-width:260px;margin-top:12px"><label>Jumlah foto dalam frame (manual)</label><input id="slotCount" type="number" min="1" max="8" value="${slots.length}"><small class="field-help">Atur jumlah langsung atau gunakan tombol tambah/hapus slot.</small></div>
 <div class="panel" style="margin-top:14px"><h3>QR Google Drive di Dalam Frame</h3><label class="frame-enable-check"><input id="driveQrEnabled" type="checkbox" ${qrEnabled?'checked':''}><span>Sisipkan QR Google Drive ke hasil JPG untuk dicetak</span></label><p class="muted">QR menggunakan tautan folder Google Drive sesi. Seret kotak QR pada pratinjau untuk mengatur posisi dan gunakan pegangan sudut untuk mengubah ukuran. QR baru dirender setelah tautan folder sesi tersedia.</p></div><div class="layout-editor-preview" id="layoutEditorPreview"><img id="framePreviewImage" alt="Frame PNG terpilih" hidden><div id="slotPreviewLayer"></div></div><div id="slotSourceControls" class="slot-source-controls"></div>
 <div class="notice">Atur slot langsung pada pratinjau: seret kotak bernomor untuk memindahkan, lalu seret pegangan di sudut kanan bawah untuk mengubah ukurannya. Perubahan tersimpan saat menekan Simpan Frame & Layout.</div>
 <div class="actions"><button class="btn" id="saveLayout">Simpan Frame & Layout</button></div><div id="layoutStatus" class="notice">Layout akan dipakai pada sesi pemotretan berikutnya.</div></div>`;
 const preview=$('#layoutEditorPreview'),frameImg=$('#framePreviewImage'),layer=$('#slotPreviewLayer');
 const arrange=(n)=>Array.from({length:n},(_,i)=>{const cols=$('#layoutSize').value==='2R Strip'?1:(n===1?1:2),rows=Math.ceil(n/cols),w=86/cols,h=84/rows;return{x:7+(i%cols)*w,y:8+Math.floor(i/cols)*h,w:w-3,h:h-3,photo_index:i};});
 const draw=()=>{const id=$('#savedFrames').value;selectedFrame=id;frameImg.hidden=!id;frameImg.onload=()=>{if(frameImg.naturalWidth&&frameImg.naturalHeight)preview.style.aspectRatio=`${frameImg.naturalWidth}/${frameImg.naturalHeight}`;};frameImg.onerror=()=>{frameImg.hidden=true;$('#layoutStatus').textContent='Pratinjau PNG tidak dapat dimuat. Periksa file frame atau backend.';};frameImg.src=id?`http://127.0.0.1:8765/api/frames/${id}.png?preview=${Date.now()}`:'';if(!id)preview.style.aspectRatio=$('#layoutSize').value==='2R Strip'?'1/3':($('#layoutSize').value==='4R'&&$('#layoutOrientation').value==='portrait'?'2/3':'3/2');$('#slotCount').value=slots.length;drawPreviewOnly();};
 frameList.forEach(f=>{const enabled=document.querySelector(`[data-frame-enabled="${f.id}"]`);if(enabled)enabled.onchange=async()=>{enabled.disabled=true;try{await api('/api/frames/enabled',{method:'POST',body:JSON.stringify({frame_id:f.id,enabled:enabled.checked})});f.enabled=enabled.checked;f.active=enabled.checked;$('#layoutStatus').textContent=`Frame ${f.name} ${enabled.checked?'ditampilkan':'disembunyikan'} pada pilihan sesi foto.`;}catch(e){enabled.checked=!enabled.checked;$('#layoutStatus').textContent='Gagal menyimpan pilihan frame: '+e.message;}finally{enabled.disabled=false;}};const edit=document.querySelector(`[data-frame-edit="${f.id}"]`);if(edit)edit.onclick=()=>{$('#savedFrames').value=f.id;draw();document.querySelector('#layoutEditorPreview').scrollIntoView({behavior:'smooth',block:'center'});$('#layoutStatus').textContent=`Mode edit: ${f.name}. Atur slot lalu Simpan Frame & Layout.`;};const del=document.querySelector(`[data-frame-delete="${f.id}"]`);if(del)del.onclick=async()=>{if(!(await kacaConfirm(`Hapus frame ${f.name}?`)))return;try{await api(`/api/frames/${f.id}/delete`);if(settings.frameId===f.id){settings.frameId='';await saveScopedSettings();}await renderFrames();}catch(e){$('#layoutStatus').textContent='Gagal menghapus frame: '+e.message;}};});
 const drawPreviewOnly=()=>{layer.innerHTML=slots.map((v,i)=>`<div class="editor-slot" data-slot-index="${i}" style="left:${v.x}%;top:${v.y}%;width:${v.w}%;height:${v.h}%"><span>${i+1} · Foto ${Number(v.photo_index??i)+1}</span><i class="slot-resize-handle" title="Ubah ukuran slot"></i></div>`).join('')+(qrEnabled?`<div class="editor-drive-qr" id="editorDriveQr" style="left:${qrLayout.x}%;top:${qrLayout.y}%;width:${qrLayout.w}%;height:${qrLayout.h}%"><span>QR<br>DRIVE</span><i class="slot-resize-handle" title="Ubah ukuran QR"></i></div>`:'');$('#slotSourceControls').innerHTML=slots.map((v,i)=>`<div class="field slot-source-row"><label>Slot ${i+1} menggunakan foto</label><select data-slot-source="${i}">${Array.from({length:8},(_,n)=>`<option value="${n}" ${Number(v.photo_index??i)===n?'selected':''}>Foto ${n+1}${slots.some((q,j)=>j!==i&&Number(q.photo_index??j)===n)?' · duplikat':''}</option>`).join('')}</select></div>`).join('');$('#slotSourceControls').querySelectorAll('[data-slot-source]').forEach(sel=>sel.onchange=()=>{slots[Number(sel.dataset.slotSource)].photo_index=Number(sel.value);drawPreviewOnly();});layer.querySelectorAll('.editor-slot').forEach(el=>{const index=Number(el.dataset.slotIndex);let action='',startX=0,startY=0,initial=null;const begin=(ev,mode)=>{ev.preventDefault();ev.stopPropagation();action=mode;startX=ev.clientX;startY=ev.clientY;initial={...slots[index]};el.setPointerCapture?.(ev.pointerId);};el.onpointerdown=ev=>{if(ev.target.classList.contains('slot-resize-handle'))begin(ev,'resize');else begin(ev,'move');};el.onpointermove=ev=>{if(!action||!initial)return;const rect=preview.getBoundingClientRect(),dx=(ev.clientX-startX)/rect.width*100,dy=(ev.clientY-startY)/rect.height*100;const v=slots[index];if(action==='move'){v.x=Math.max(0,Math.min(100-v.w,initial.x+dx));v.y=Math.max(0,Math.min(100-v.h,initial.y+dy));}else{v.w=Math.max(4,Math.min(100-initial.x,initial.w+dx));v.h=Math.max(4,Math.min(100-initial.y,initial.h+dy));}el.style.left=v.x+'%';el.style.top=v.y+'%';el.style.width=v.w+'%';el.style.height=v.h+'%';};const end=()=>{action='';initial=null;};el.onpointerup=end;el.onpointercancel=end;});const qrEl=$('#editorDriveQr');if(qrEl){let action='',sx=0,sy=0,initial=null;const begin=(ev,mode)=>{ev.preventDefault();ev.stopPropagation();action=mode;sx=ev.clientX;sy=ev.clientY;initial={...qrLayout};qrEl.setPointerCapture?.(ev.pointerId);};qrEl.onpointerdown=ev=>begin(ev,ev.target.classList.contains('slot-resize-handle')?'resize':'move');qrEl.onpointermove=ev=>{if(!action||!initial)return;const rect=preview.getBoundingClientRect(),dx=(ev.clientX-sx)/rect.width*100,dy=(ev.clientY-sy)/rect.height*100;if(action==='move'){qrLayout.x=Math.max(0,Math.min(100-qrLayout.w,initial.x+dx));qrLayout.y=Math.max(0,Math.min(100-qrLayout.h,initial.y+dy));}else{const delta=Math.max(-initial.w+6,Math.min(100-Math.max(initial.x,initial.y)-initial.w,Math.max(dx,dy)));qrLayout.w=Math.max(6,Math.min(100-qrLayout.x,initial.w+delta));qrLayout.h=qrLayout.w;}qrEl.style.left=qrLayout.x+'%';qrEl.style.top=qrLayout.y+'%';qrEl.style.width=qrLayout.w+'%';qrEl.style.height=qrLayout.h+'%';};const end=()=>{action='';initial=null;};qrEl.onpointerup=end;qrEl.onpointercancel=end;}};
 $('#driveQrEnabled').onchange=()=>{qrEnabled=$('#driveQrEnabled').checked;drawPreviewOnly();};const syncCustomSize=()=>{const show=$('#layoutSize').value==='Custom';document.querySelectorAll('.custom-size-field').forEach(el=>el.style.display=show?'block':'none');};$('#layoutSize').onchange=syncCustomSize;syncCustomSize();$('#savedFrames').onchange=()=>{const next=$('#savedFrames').value;const saved=frameLayouts[next]||(next===settings.frameId?settings.layoutSlots:null);if(Array.isArray(saved)&&saved.length)slots=saved.map((v,i)=>({x:Number(v.x)*100,y:Number(v.y)*100,w:Number(v.w)*100,h:Number(v.h)*100,photo_index:Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i}));else slots=fresh();qrLayout=loadQrLayout(next);draw();};$('#addSlot').onclick=()=>{if(slots.length>=8)return;slots.push({x:10,y:10,w:35,h:35,photo_index:slots.length});draw();};$('#duplicateSlot').onclick=()=>{if(slots.length>=8||!slots.length)return;const last=slots[slots.length-1];slots.push({...last,x:Math.min(95,last.x+5),y:Math.min(95,last.y+5)});draw();$('#layoutStatus').textContent='Slot diduplikasi. Foto sumber sama digunakan kembali pada slot baru; jumlah foto yang perlu diambil tidak bertambah.';};$('#removeSlot').onclick=()=>{if(slots.length>1){slots.pop();draw();}};$('#resetSlots').onclick=()=>{slots=arrange(slots.length);draw();};$('#slotCount').onchange=()=>{const n=Math.max(1,Math.min(8,Number($('#slotCount').value)||1));while(slots.length<n)slots.push({x:10,y:10,w:35,h:35,photo_index:slots.length});while(slots.length>n)slots.pop();draw();};
 $('#createFramePng').onclick=async()=>{try{const size=$('#layoutSize').value,orient=size==='2R Strip'?'portrait':$('#layoutOrientation').value,dpi=Number(settings.printDpi||300);const canvas=document.createElement('canvas');if(size==='2R Strip'){canvas.width=2*dpi;canvas.height=6*dpi;}else if(size==='Custom'){canvas.width=Math.round(Math.max(1,Number($('#customWidth').value)||4)*dpi);canvas.height=Math.round(Math.max(1,Number($('#customHeight').value)||6)*dpi);}else{canvas.width=orient==='portrait'?4*dpi:6*dpi;canvas.height=orient==='portrait'?6*dpi:4*dpi;}const ctx=canvas.getContext('2d');ctx.fillStyle=$('#frameBgColor').value;ctx.fillRect(0,0,canvas.width,canvas.height);const scale=canvas.width/1800;ctx.strokeStyle=$('#frameAccentColor').value;ctx.lineWidth=Math.max(8,canvas.width*.008);ctx.strokeRect(ctx.lineWidth/2,ctx.lineWidth/2,canvas.width-ctx.lineWidth,canvas.height-ctx.lineWidth);ctx.fillStyle=$('#frameAccentColor').value;ctx.textAlign='center';ctx.font=`bold ${Math.round(canvas.width*.045)}px Arial`;ctx.fillText($('#frameTitle').value||'KACA.ID',canvas.width/2,canvas.height*.07);ctx.font=`${Math.round(canvas.width*.018)}px Arial`;ctx.fillText($('#frameFooter').value||'SAY CHEESE, SAY KACA',canvas.width/2,canvas.height*.965);ctx.globalCompositeOperation='destination-out';for(const v of slots){const x=v.x/100*canvas.width,y=v.y/100*canvas.height,w=v.w/100*canvas.width,h=v.h/100*canvas.height;ctx.clearRect(x,y,w,h);}ctx.globalCompositeOperation='source-over';const r=await api('/api/frames/import',{method:'POST',body:JSON.stringify({name:($('#frameTitle').value||'Frame KACA.ID')+'.png',data_url:canvas.toDataURL('image/png'),event_id:activeEvent()?.id||null})});const opt=document.createElement('option');opt.value=r.frame.id;opt.textContent=$('#frameTitle').value||'Frame KACA.ID';$('#savedFrames').append(opt);$('#savedFrames').value=r.frame.id;selectedFrame=r.frame.id;$('#layoutStatus').textContent='Frame baru berhasil dibuat dan disimpan sebagai PNG transparan.';draw();}catch(err){$('#layoutStatus').textContent='Gagal membuat frame: '+err.message;}};
 $('#frameFile').onchange=async e=>{const file=e.target.files?.[0];if(!file)return;if(file.type!=='image/png'){alert('Pilih file PNG.');return;}if(file.size>15*1024*1024){alert('Ukuran maksimal 15 MB.');return;}try{const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file);});const r=await api('/api/frames/import',{method:'POST',body:JSON.stringify({name:file.name,data_url:data,event_id:activeEvent()?.id||null})});const opt=document.createElement('option');opt.value=r.frame.id;opt.textContent=file.name;$('#savedFrames').append(opt);$('#savedFrames').value=r.frame.id;selectedFrame=r.frame.id;$('#layoutStatus').textContent=`Frame ${file.name} berhasil diimpor (${r.frame.width} × ${r.frame.height}).`;draw();}catch(err){$('#layoutStatus').textContent='Gagal mengimpor frame: '+err.message;}};
 draw();
 $('#saveLayout').onclick=async()=>{settings.paperSize=$('#layoutSize').value;settings.orientation=$('#layoutOrientation').value;settings.customWidth=Math.max(1,Math.min(20,Number($('#customWidth').value)||4));settings.customHeight=Math.max(1,Math.min(20,Number($('#customHeight').value)||6));settings.frameSlots=String(slots.length);settings.frameId=$('#savedFrames').value||'';settings.layoutSlots=slots.map((v,i)=>({x:v.x/100,y:v.y/100,w:v.w/100,h:v.h/100,photo_index:Number.isInteger(Number(v.photo_index))?Number(v.photo_index):i}));settings.frameLayouts=settings.frameLayouts&&typeof settings.frameLayouts==='object'?settings.frameLayouts:{};if(settings.frameId)settings.frameLayouts[settings.frameId]=settings.layoutSlots.map(v=>({...v}));settings.driveQrEnabled=qrEnabled;settings.driveQrLayout={x:qrLayout.x/100,y:qrLayout.y/100,w:qrLayout.w/100,h:qrLayout.h/100};settings.driveQrLayouts=settings.driveQrLayouts&&typeof settings.driveQrLayouts==='object'?settings.driveQrLayouts:{};if(settings.frameId)settings.driveQrLayouts[settings.frameId]={...settings.driveQrLayout};frameLayouts=settings.frameLayouts;await saveScopedSettings();$('#layoutStatus').textContent=`Tersimpan: ${slots.length} slot foto${settings.frameId?' · frame PNG aktif':''}. Pengaturan posisi akan dipakai untuk JPG dan video Live Photo.`;};
}
async function renderFilters(){const filters=[['original','Original Kamera · tanpa filter'],['sepia','Sepia · klasik cokelat antik'],['chrome','Chrome / Vivid · warna tajam'],['vintage','Vintage · nostalgia'],['mono','Hitam Putih · monokrom'],['cool','Cool / Cinematic · biru dingin'],['pencil','Sketsa Pensil · arsiran hitam putih'],['cartoon','Kartun / Ilustrasi · warna lembut dan garis tegas']];$('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / FILTER FOTO</div><h3>Filter Pemotretan</h3><p class="muted">Filter diterapkan saat foto disimpan. File asli kamera tetap disimpan terpisah dan tidak diubah.</p><div class="filter-options">${filters.map(([name,desc])=>`<label class="filter-option"><input type="radio" name="photoFilter" value="${name}" ${(filters.some(([id])=>id===settings.defaultFilter)?settings.defaultFilter:'original')===name?'checked':''}><span><b>${name}</b><small>${desc}</small></span></label>`).join('')}</div><div class="actions"><button class="btn" id="saveFilter">Simpan Filter</button></div><div id="filterStatus" class="notice">Filter aktif: ${settings.defaultFilter||'sepia'}.</div></div>`;$('#saveFilter').onclick=async()=>{settings.defaultFilter=$('input[name="photoFilter"]:checked').value;await saveScopedSettings();$('#filterStatus').textContent='Filter '+settings.defaultFilter+' tersimpan.';};}
async function renderPrinters(){
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / PRINT MANAGEMENT</div><h3>Printer & Pengaturan Kertas</h3><p class="muted">Daftar printer dibaca dari Windows. Pilih printer aktif, atur ukuran kertas, lalu simpan sebagai konfigurasi KACA.ID.</p><div class="actions"><button class="btn secondary" id="refreshPrinters">Deteksi Ulang Printer</button></div><div class="form-grid"><div class="field"><label>Printer Windows</label><select id="printerSelect"><option>Memuat printer…</option></select></div><div class="field"><label>Ukuran kertas KACA.ID</label><select id="printerPaper"><option>4R</option><option>2R Strip</option><option>Custom</option></select></div><div class="field"><label>Ukuran fisik dari driver Windows</label><select id="printerDriverPaper"><option value="">Otomatis sesuai ukuran KACA.ID</option></select><small class="field-help">Daftar disinkronkan dari driver setelah Properties printer dibuka atau printer dipilih.</small></div><div class="field" id="printerCustomW"><label>Lebar custom (inci)</label><input id="printerWidth" type="number" min="1" max="20" step="0.1" value="${settings.customWidth||4}"></div><div class="field" id="printerCustomH"><label>Tinggi custom (inci)</label><input id="printerHeight" type="number" min="1" max="20" step="0.1" value="${settings.customHeight||6}"></div><div class="field"><label>DPI cetak</label><select id="printerDpi"><option value="300">300 DPI</option><option value="600">600 DPI</option></select></div><div class="field"><label>Mode tepi cetak</label><select id="printerBorderless"><option value="false">Dengan Border / Margin</option><option value="true">Tanpa Border (Borderless)</option></select><small class="field-help" id="borderlessSupport">Opsi borderless akan diverifikasi dari paper size yang disediakan driver printer.</small></div></div><div class="actions wrap"><button class="btn secondary" id="openPrinterProperties">Properties Printer Windows</button><button class="btn" id="savePrinterSettings">Jadikan Printer Default & Simpan</button></div><div id="printerStatus" class="notice">Pengaturan printer belum dimuat.</div><div class="notice">Catatan: ukuran kertas disimpan pada konfigurasi KACA.ID. Ukuran fisik yang benar-benar tersedia dan opsi borderless tetap mengikuti driver printer Windows.</div></div>`;
 const status=$('#printerStatus');$('#printerPaper').value=settings.paperSize||'4R';$('#printerDpi').value=String(settings.printDpi||300);$('#printerBorderless').value=String(!!settings.printBorderless);const sync=()=>{const custom=$('#printerPaper').value==='Custom';$('#printerCustomW').style.display=custom?'block':'none';$('#printerCustomH').style.display=custom?'block':'none';};$('#printerPaper').onchange=sync;sync();
 async function load(){try{const r=await api('/api/printers');const sel=$('#printerSelect');sel.innerHTML=r.printers.length?r.printers.map(p=>`<option value="${p.name.replaceAll('&','&amp;').replaceAll('\"','&quot;')}" ${p.default?'selected':''}>${p.name}${p.default?' (Default)':''}${p.offline?' · Offline':''}</option>`).join(''):'<option value="">Tidak ada printer Windows terdeteksi</option>';if(settings.printerName)sel.value=settings.printerName;status.textContent=r.printers.length?`${r.printers.length} printer ditemukan.`:(r.error||'Windows tidak mengembalikan daftar printer. Pastikan printer terpasang di Settings > Bluetooth & devices > Printers & scanners.');}catch(e){status.textContent='Gagal membaca printer: '+e.message;}}$('#refreshPrinters').onclick=load;await load();$('#openPrinterProperties').onclick=async()=>{const name=$('#printerSelect').value;if(!name){status.textContent='Pilih printer Windows terlebih dahulu.';return;}const btn=$('#openPrinterProperties');try{btn.disabled=true;status.textContent='Membuka dialog Properties printer Windows…';const result=await window.kaca.openPrinterProperties(name);if(!result?.ok)throw new Error('Dialog Properties printer gagal dibuka (kode '+result?.code+').');status.textContent='Dialog Properties ditutup. Membaca ulang ukuran kertas dan kemampuan borderless dari driver…';await checkBorderless();}catch(e){status.textContent='Tidak dapat membuka Properties printer: '+e.message;}finally{btn.disabled=false;}};const checkBorderless=async()=>{try{const r=await api('/api/printers/paper-sizes',{method:'POST',body:JSON.stringify({name:$('#printerSelect').value})});const borderNames=(r.paper_sizes||[]).filter(x=>/Borderless|Border Free|No Margin|Tanpa Tepi|Border-Free/i.test(x.name||'')).map(x=>x.name);const driverSelect=$('#printerDriverPaper'),savedDriver=settings.printerDriverPaper||'';driverSelect.innerHTML='<option value="">Otomatis sesuai ukuran KACA.ID</option>'+(r.paper_sizes||[]).map(x=>`<option value="${String(x.name).replaceAll('&','&amp;').replaceAll('"','&quot;')}">${x.name} · ${(Number(x.width||0)/100).toFixed(2)} × ${(Number(x.height||0)/100).toFixed(2)} inci</option>`).join('');if(savedDriver&&[...driverSelect.options].some(o=>o.value===savedDriver))driverSelect.value=savedDriver;$('#borderlessSupport').textContent='Daftar ukuran driver berhasil disinkronkan. Nama opsi tanpa tepi berbeda antar-merek; pilih ukuran Borderless jika tersedia atau atur mode tanpa tepi melalui Properties printer Windows. KACA.ID tidak menolak printer hanya karena nama ukuran tidak mengandung kata Borderless.';$('#printerBorderless').querySelector('option[value="true"]').disabled=false;}catch(e){$('#borderlessSupport').textContent='Tidak dapat membaca kemampuan driver: '+e.message;}};$('#printerSelect').onchange=checkBorderless;if($('#printerSelect').value)await checkBorderless();$('#savePrinterSettings').onclick=async()=>{try{const name=$('#printerSelect').value;if(name)await api('/api/printers/default',{method:'POST',body:JSON.stringify({name})});settings.printerName=name;settings.paperSize=$('#printerPaper').value;settings.printerDriverPaper=$('#printerDriverPaper').value;settings.customWidth=Number($('#printerWidth').value)||4;settings.customHeight=Number($('#printerHeight').value)||6;settings.printDpi=Number($('#printerDpi').value)||300;settings.printBorderless=$('#printerBorderless').value==='true';await saveScopedSettings();status.textContent=`Tersimpan: ${name||'printer belum dipilih'} · ${settings.paperSize} · ${settings.printDpi} DPI.`;}catch(e){status.textContent='Gagal menyimpan printer: '+e.message;}};
}
function kacaConfirm(message){
 return new Promise(resolve=>{
  const overlay=document.createElement('div');overlay.className='kaca-confirm-overlay';overlay.setAttribute('role','alertdialog');overlay.setAttribute('aria-modal','true');
  overlay.innerHTML=`<div class="kaca-confirm-card"><h3>Konfirmasi Operator</h3><p>${esc(message)}</p><div class="actions"><button type="button" class="btn secondary" data-confirm-cancel>Batal</button><button type="button" class="btn" data-confirm-yes>Ya, Lanjutkan</button></div></div>`;
  document.body.appendChild(overlay);let done=false;
  const close=value=>{if(done)return;done=true;document.removeEventListener('keydown',onkey,true);overlay.remove();resolve(value);};
  const onkey=e=>{if(e.key==='Escape')close(false);};document.addEventListener('keydown',onkey,true);
  overlay.querySelector('[data-confirm-cancel]').onclick=()=>close(false);
  overlay.querySelector('[data-confirm-yes]').onclick=()=>close(true);
  overlay.addEventListener('click',e=>{if(e.target===overlay)close(false);});
  setTimeout(()=>overlay.querySelector('[data-confirm-cancel]')?.focus(),30);
 });
}
function askKacaWhatsAppDetails(){
 return new Promise(resolve=>{
  const overlay=document.createElement('div');
  overlay.className='kaca-share-overlay';overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');
  overlay.innerHTML=`<form class="kaca-share-card"><div class="eyebrow2">KACA.ID / BAGIKAN HASIL</div><h3>Kirim Hasil via WhatsApp</h3><p>Masukkan nomor WhatsApp pelanggan. Link akan dikirim melalui metode yang dipilih di Pengaturan Umum.</p><label for="shareTargetNumber">Nomor WhatsApp tujuan</label><input id="shareTargetNumber" type="tel" inputmode="tel" placeholder="08xxxxxxxxxx" autocomplete="tel" required maxlength="17"><label class="kaca-share-consent"><input type="checkbox" id="shareConsent"> Pelanggan menyetujui menerima tautan hasil sesi lewat WhatsApp.</label><p class="kaca-share-mode">Metode aktif: <b>${settings.waDeliveryMode==='gateway_fonnte'?'Gateway Fonnte (tanpa WhatsApp Web)':settings.waDeliveryMode==='click_to_chat'?'Click-to-Chat (membuka WhatsApp)':'WhatsApp Cloud API'}</b></p><small class="pin-error" id="shareInputError" aria-live="polite"></small><div class="actions"><button type="button" class="btn secondary" data-share-cancel>Batal</button><button type="submit" class="btn" data-share-send>Kirim Tautan</button></div></form>`;
  document.body.appendChild(overlay);
  const input=overlay.querySelector('#shareTargetNumber'),form=overlay.querySelector('form');
  let done=false;
  const close=value=>{if(done)return;done=true;document.removeEventListener('keydown',escapeHandler,true);if(typeof closeKacaKeyboard==='function')closeKacaKeyboard();overlay.remove();resolve(value);};
  const escapeHandler=e=>{if(e.key==='Escape'){e.stopPropagation();close(null);}};
  document.addEventListener('keydown',escapeHandler,true);
  overlay.querySelector('[data-share-cancel]').onclick=()=>close(null);
  overlay.addEventListener('click',e=>{if(e.target===overlay)close(null);});
  form.onsubmit=e=>{e.preventDefault();const phone=input.value.trim(),digits=phone.replace(/\D/g,'');if(!/^((0|62|\+62|8)[0-9]{8,15})$/.test(phone.replace(/[\s()-]/g,''))||digits.length<10){overlay.querySelector('#shareInputError').textContent='Nomor tidak valid. Masukkan contoh 082312345678.';input.focus();return;}if(!overlay.querySelector('#shareConsent').checked){overlay.querySelector('#shareInputError').textContent='Centang persetujuan pelanggan terlebih dahulu.';return;}close({phone,consent:true});};
  setTimeout(()=>{if(overlay.isConnected){input.focus();input.select();}},60);
 });
}
async function shareKacaSession(session, channel='whatsapp'){
 const sid=String(session?.id||'');if(!sid)throw new Error('ID sesi tidak tersedia.');
 // Ask for recipient first; an unavailable Drive link must not trigger a 20s modal wait.
 const details=channel==='whatsapp'?await askKacaWhatsAppDetails():null;
 if(channel==='whatsapp'&&!details)return 'Dibatalkan.';
 let status=await api(`/api/session/${sid}/render-status`);
 let url=status.drive_url||session.drive_url;
 if(!url&&status.drive_status==='provisioning'){
  for(let attempt=0;attempt<12&&!url;attempt++){
   await new Promise(resolve=>setTimeout(resolve,1000));
   status=await api(`/api/session/${sid}/render-status`);url=status.drive_url||'';
  }
 }
 if(!url)throw new Error(status.drive_error||'Tautan Google Drive belum tersedia. Hubungkan Drive dan tunggu folder sesi dibuat.');
 const message=`Halo! Hasil foto sesi KACA.ID Anda sudah tersedia: ${url}\nTerima kasih telah menggunakan KACA.ID.`;
 if(channel==='email'){
  const mailto='mailto:?subject='+encodeURIComponent('Hasil Foto KACA.ID')+'&body='+encodeURIComponent(message);
  await window.kaca.openExternal(mailto);return 'Aplikasi email dibuka. Periksa lalu kirim pesan.';
 }
 const mode=settings.waDeliveryMode||'cloud_api';
 if(mode==='gateway_fonnte'){
  const response=await api('/api/whatsapp/fonnte/send',{method:'POST',body:JSON.stringify({session_id:sid,phone:details.phone,consent:details.consent})});
  return response.duplicate?'Permintaan sebelumnya sudah diterima gateway Fonnte untuk nomor ini.':`Fonnte menerima permintaan pengiriman (${response.request_id||response.message_id||'antrean gateway'}). Ini belum membuktikan pesan telah diterima pelanggan.`;
 }
 if(mode==='click_to_chat'){
  const digits=details.phone.replace(/\D/g,'');const normalized=digits.startsWith('0')?'62'+digits.slice(1):digits.startsWith('8')?'62'+digits:digits;
  await window.kaca.openExternal('https://wa.me/'+normalized+'?text='+encodeURIComponent(message));
  return 'WhatsApp dibuka. Periksa pesan lalu tekan Kirim.';
 }
 const result=await api('/api/whatsapp/send',{method:'POST',body:JSON.stringify({kind:'session',session_id:sid,phone:details.phone,consent:true})});
 return result.duplicate?'Nomor ini sudah memiliki antrean pengiriman.':'Permintaan dimasukkan ke antrean WhatsApp Cloud API.';
}

async function renderSessions(page){
 $('#content').innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / ${page.toUpperCase()}</div><h3>${page==='archive'?'Arsip Sesi':'Output & Cetak'}</h3><p class="muted">Daftar hasil tersimpan berdasarkan waktu. Thumbnail menampilkan foto akhir dalam frame; file pendukung disembunyikan dari daftar.</p><div id="sessionList" class="session-list"><div class="empty">Memuat arsip…</div></div></div>`;
  if(page==='output'){
    const settingsPanel=document.createElement('section');settingsPanel.className='panel retention-settings-panel';
    settingsPanel.innerHTML=`<div class="eyebrow2">KACA.ID / AUTO CLEANUP</div><h3>Hapus Hasil Otomatis</h3><p class="muted">Durasi dihitung sejak sesi selesai. Lokal dan Google Drive punya batas waktu berbeda. Penghapusan lokal permanen; folder Google Drive dipindahkan ke Sampah (masih bisa dipulihkan). Pengaturan awal nonaktif.</p><div class="form-grid"><div class="field"><label><input type="checkbox" id="localRetentionEnabled"> Hapus otomatis file lokal</label><input id="localRetentionDays" type="number" min="1" max="3650" value="30"><small class="field-help">Durasi penyimpanan lokal (hari). Berkas sesi yang habis masa simpan tidak muncul lagi dalam arsip aplikasi.</small></div><div class="field"><label><input type="checkbox" id="driveRetentionEnabled"> Hapus otomatis folder sesi Google Drive</label><input id="driveRetentionDays" type="number" min="1" max="3650" value="30"><small class="field-help">Durasi penyimpanan Drive (hari). Hanya folder sesi KACA yang terverifikasi di dalam folder KACA STUDIO/Event yang dapat dipindahkan ke Sampah.</small></div></div><div class="actions wrap"><button type="button" class="btn" id="saveRetention">Simpan Durasi Otomatis</button><button type="button" class="btn secondary" id="runRetention">Periksa Kedaluwarsa Sekarang</button></div><div class="notice" id="retentionStatus">Memuat pengaturan penyimpanan…</div>`;
    $('#content').appendChild(settingsPanel);
    const note=$('#retentionStatus');
    try{
      const current=await api('/api/retention/status');
      $('#localRetentionEnabled').checked=!!current.local_enabled;
      $('#driveRetentionEnabled').checked=!!current.drive_enabled;
      $('#localRetentionDays').value=Number(current.local_days||30);
      $('#driveRetentionDays').value=Number(current.drive_days||30);
      note.textContent='Durasi dihitung dari tanggal selesai sesi. Tidak ada file yang dihapus selama opsi nonaktif.';
    }catch(e){note.textContent='Pengaturan retensi belum tersedia: '+e.message+' · Periksa apakah backend telah diperbarui.';}
    $('#saveRetention').onclick=async()=>{
      const config={local_enabled:$('#localRetentionEnabled').checked,drive_enabled:$('#driveRetentionEnabled').checked,
        local_days:Number($('#localRetentionDays').value),drive_days:Number($('#driveRetentionDays').value)};
      if((config.local_enabled||config.drive_enabled)&&!(await kacaConfirm('Aktifkan penghapusan otomatis? Semua sesi lama yang telah melewati batas juga dapat dihapus pada pemeriksaan berikutnya. Penghapusan lokal tidak dapat dibatalkan.')))return;
      try{
        const result=await api('/api/retention/config',{method:'POST',body:JSON.stringify(config)});
        note.textContent='Pengaturan disimpan. Lokal: '+(result.local_enabled?result.local_days+' hari':'nonaktif')+' · Drive: '+(result.drive_enabled?result.drive_days+' hari':'nonaktif')+'.';
      }catch(e){note.textContent='Gagal menyimpan durasi: '+e.message;}
    };
    $('#runRetention').onclick=async()=>{
      if(!(await kacaConfirm('Periksa seluruh sesi selesai sekarang? File lokal kedaluwarsa akan dihapus permanen dan folder Drive yang kedaluwarsa dipindahkan ke Sampah.')))return;
      try{const result=await api('/api/retention/run',{method:'POST',body:'{}'});note.textContent=`Selesai diperiksa: ${result.scanned} sesi · ${result.local_deleted} lokal dihapus · ${result.drive_trashed} folder Drive dipindahkan ke Sampah.${(result.errors||[]).length?' Kendala: '+result.errors.slice(0,2).join('; '):''}`;await renderSessions('output');}
      catch(e){note.textContent='Gagal menjalankan pemeriksaan: '+e.message;}
    };
  }
 const box=$('#sessionList');try{const r=await api('/api/sessions');r.sessions=(r.sessions||[]).filter(s=>String(s.event_id||s.settings?.event_id||'')===String(activeEvent()?.id||''));if(!r.sessions.length){box.innerHTML='<div class="empty">Belum ada sesi selesai. Buat sesi pertama melalui Capture Studio.</div>';return;}
 let sessionPage=1;
 const pager=document.createElement('nav');pager.className='kaca-pager';pager.setAttribute('aria-label','Halaman hasil foto');box.insertAdjacentElement('afterend',pager);
 const showSessionPage=()=>{
   sessionPage=Math.min(sessionPage,Math.max(1,Math.ceil(r.sessions.length/10)));
   renderKacaPager(pager,r.sessions.length,sessionPage,next=>{sessionPage=next;showSessionPage();box.scrollIntoView({block:'start',behavior:'smooth'});});
 box.innerHTML=r.sessions.slice((sessionPage-1)*10,sessionPage*10).map(s=>{const sid=s.id,thumb=`http://127.0.0.1:8765/api/session/${sid}/output.jpg`;return `<article class="output-session-row"><div class="output-thumb"><img src="${thumb}?v=${encodeURIComponent(s.finished_at||s.created_at||'')}" alt="Thumbnail hasil sesi"></div><div class="output-session-info"><b>${new Date(s.finished_at||s.created_at).toLocaleString('id-ID')}</b><small>${s.id} · ${s.photos?.length||0} foto · ${s.paper_size||'4R'} · ${s.session_mode==='timed'?'Mode durasi':'Mode jumlah foto'}</small><span class="output-status">${s.live_output?'Live Photo tersedia':'Foto frame siap'}${s.gif_output?' · GIF tersedia':''} · Google Drive: ${esc(s.drive_status||'belum diunggah')}</span>${s.drive_url?`<a class="text-link" href="${esc(s.drive_url)}" target="_blank" rel="noreferrer">Buka folder Google Drive</a>`:''}</div><div class="output-session-actions"><button class="btn secondary small" data-view="${sid}">Lihat Hasil</button><button class="btn secondary small" data-print="${sid}">Cetak</button><a class="btn secondary small" download="KACA-ID-${sid}-Hasil.zip" href="http://127.0.0.1:8765/api/session/${sid}/download.zip">Unduh Hasil</a><button class="btn small" data-share="${sid}">Share WhatsApp</button><button class="btn secondary small" data-share-email="${sid}">Share Email</button></div></article>`;}).join('');
 box.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{const s=r.sessions.find(x=>x.id===b.dataset.view);showSessionDetail(s);});
 box.querySelectorAll('[data-print]').forEach(b=>b.onclick=async()=>{const sid=b.dataset.print;const prior=b.textContent;try{b.disabled=true;b.textContent='Mengirim…';const pr=await api(`/api/session/${sid}/print`,{method:'POST',body:JSON.stringify({printer_name:settings.printerName||'',paper_size:settings.paperSize||'4R',custom_width:Number(settings.customWidth||4),custom_height:Number(settings.customHeight||6),copies:Number(settings.printCopies||1),dpi:Number(settings.printDpi||300),borderless:!!settings.printBorderless,driver_paper_name:settings.printerDriverPaper||''})});b.textContent='Terkirim ✓';}catch(e){alert('Gagal mencetak: '+e.message);b.textContent=prior;}finally{b.disabled=false;}});
 box.querySelectorAll('[data-share]').forEach(b=>b.onclick=async()=>{const sid=b.dataset.share,session=r.sessions.find(x=>x.id===sid),prior=b.textContent;try{b.disabled=true;b.textContent='Membuka…';const result=await shareKacaSession(session,'whatsapp');if(result!=='Dibatalkan.')alert(result);}catch(e){alert('Share WhatsApp gagal: '+e.message);}finally{b.disabled=false;b.textContent=prior;}});
 box.querySelectorAll('[data-share-email]').forEach(b=>b.onclick=async()=>{const sid=b.dataset.shareEmail,session=r.sessions.find(x=>x.id===sid),prior=b.textContent;try{b.disabled=true;b.textContent='Membuka…';const result=await shareKacaSession(session,'email');alert(result);}catch(e){alert('Share Email gagal: '+e.message);}finally{b.disabled=false;b.textContent=prior;}});
 };showSessionPage();
 }catch(e){box.innerHTML=`<div class="notice">Gagal memuat arsip: ${e.message}</div>`;}
 function showSessionDetail(s){const sid=s.id,base=`http://127.0.0.1:8765/api/session/${sid}/`;const originals=(s.photos||[]).map(p=>`<div class="detail-original"><img src="${base}original/${p.original}" alt="Foto original ${p.number}"><span>Foto Original ${p.number}</span></div>`).join('');const overlay=document.createElement('div');overlay.className='session-detail-overlay';overlay.innerHTML=`<div class="session-detail-modal"><div class="session-detail-head"><div><small>KACA.ID / HASIL SESI</small><h2>Hasil Foto Anda</h2><p>${new Date(s.finished_at||s.created_at).toLocaleString('id-ID')} · ${sid}</p></div><button class="btn secondary small" data-close-detail>Tutup ✕</button></div><section class="detail-feature"><div><h3>Print / Frame JPG</h3><img src="${base}output.jpg" alt="Hasil foto dalam frame"></div>${s.live_output?`<div><h3>Live Photo dalam Frame</h3><video controls autoplay muted loop playsinline preload="metadata"><source src="${base}${esc(s.live_output_preview||'output_live.webm')}" type="${(s.live_output_preview||'output_live.webm').endsWith('.webm')?'video/webm':'video/mp4'}"><source src="${base}output_live.mp4" type="video/mp4"></video></div>`:''}</section>${s.gif_output?`<section class="detail-section"><h3>GIF Foto</h3><img class="detail-gif" src="${base}originals.gif" alt="GIF foto"></section>`:''}<section class="detail-section"><h3>Foto Original</h3><div class="detail-originals">${originals}</div></section>${s.drive_url?`<section class="detail-section event-qr-detail"><h3>QR Hasil Digital</h3><img alt="QR Google Drive sesi" src="${base}qr.png" style="width:190px;max-width:100%;background:#fff;padding:9px;border-radius:10px"><p class="muted">QR mengarah ke folder khusus sesi ini, bukan ke seluruh event.</p></section>`:''}${s.drive_url?`<section class="detail-section event-qr-detail"><h3>QR Hasil Digital</h3><img alt="QR Google Drive sesi" src="${base}qr.png" style="width:190px;max-width:100%;background:#fff;padding:9px;border-radius:10px"><p class="muted">QR mengarah ke folder khusus sesi ini, bukan ke seluruh event.</p></section>`:''}<div class="session-detail-actions">${s.drive_url?`<a class="btn secondary" href="${esc(s.drive_url)}" target="_blank" rel="noreferrer">Buka Google Drive</a>`:''}<a class="btn" download="KACA-ID-${sid}-Hasil.zip" href="${base}download.zip">Unduh Semua Hasil · ZIP</a><button class="btn secondary" data-modal-print>Cetak Frame</button><button class="btn" data-modal-share-wa>Share WhatsApp</button><button class="btn secondary" data-modal-share-email>Share Email</button></div></div>`;document.body.appendChild(overlay);overlay.querySelector('[data-close-detail]').onclick=()=>overlay.remove();overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.remove();});overlay.querySelector('[data-modal-share-wa]').onclick=async()=>{const btn=overlay.querySelector('[data-modal-share-wa]');try{btn.disabled=true;const result=await shareKacaSession(s,'whatsapp');if(result!=='Dibatalkan.')alert(result);}catch(e){alert('Share WhatsApp gagal: '+e.message);}finally{btn.disabled=false;}};overlay.querySelector('[data-modal-share-email]').onclick=async()=>{const btn=overlay.querySelector('[data-modal-share-email]');try{btn.disabled=true;alert(await shareKacaSession(s,'email'));}catch(e){alert('Share Email gagal: '+e.message);}finally{btn.disabled=false;}};overlay.querySelector('[data-modal-print]').onclick=async()=>{const btn=overlay.querySelector('[data-modal-print]');try{btn.disabled=true;btn.textContent='Mengirim…';await api(`/api/session/${sid}/print`,{method:'POST',body:JSON.stringify({printer_name:settings.printerName||'',paper_size:settings.paperSize||'4R',custom_width:Number(settings.customWidth||4),custom_height:Number(settings.customHeight||6),copies:Number(settings.printCopies||1),dpi:Number(settings.printDpi||300),borderless:!!settings.printBorderless,driver_paper_name:settings.printerDriverPaper||''})});btn.textContent='Terkirim ✓';}catch(e){alert('Gagal mencetak: '+e.message);btn.textContent='Cetak Frame';}finally{btn.disabled=false;}};}
}


async function renderEvents(){
 const content=$('#content'),ev=activeEvent();
 const list=eventStore.events.map(e=>`<div class="event-row ${ev?.id===e.id?'selected':''}"><div><strong>${esc(e.name)}</strong><small>${esc(e.type||'Event')} · ${esc(e.date||'Tanggal belum ditentukan')} · ${ev?.id===e.id?'EVENT AKTIF':'Tidak aktif'}</small></div><div class="actions wrap"><button type="button" class="btn secondary small" data-event-edit="${e.id}">Atur</button><button type="button" class="btn small" data-event-activate="${e.id}" ${ev?.id===e.id?'disabled':''}>Aktifkan</button><button type="button" class="btn secondary small" data-event-delete="${e.id}">Hapus</button></div></div>`).join('');
 content.innerHTML=`<section class="panel"><div class="eyebrow2">KACA.ID / EVENT PROFILES</div><h3>Manajemen Event</h3><p class="muted">Pengaturan Wedding, Birthday, Corporate, dan event lain disimpan terpisah dari sesi umum. Frame event tidak ditampilkan pada event lain.</p><div class="event-status">${ev?'Aktif: '+esc(ev.name)+' — konfigurasi event berlaku pada Dashboard, Foto, Video, Frame, dan Cetak.':'Mode Umum aktif — menggunakan konfigurasi standar booth.'}</div><p class="muted">Hasil Event otomatis disimpan terpisah di lokal dan Google Drive (jika terhubung). Setiap sesi memiliki QR sendiri agar tamu hanya membuka folder hasil sesinya.</p><div class="actions"><button class="btn secondary" id="deactivateEvent" ${ev?'':'disabled'}>Kembali ke Mode Umum</button><button class="btn" id="openEventArchive" ${ev?'':'disabled'}>Lihat Hasil Event Aktif</button></div><h3>Tambah Event</h3><div class="form-grid"><div class="field"><label>Nama Event</label><input id="eventNewName" maxlength="100" placeholder="Wedding Aldi & Diah"></div><div class="field"><label>Tanggal</label><input id="eventNewDate" type="date"></div><div class="field"><label>Kategori</label><select id="eventNewType"><option>Wedding</option><option>Birthday</option><option>Corporate</option><option>Graduation</option><option>Event</option></select></div></div><div class="actions"><button class="btn" id="eventAdd">+ Tambahkan Event</button></div><div class="notice" id="eventNotice">Perubahan event tersimpan secara lokal dan tidak mengubah konfigurasi umum.</div><h3>Daftar Event</h3><div class="event-list">${list||'<div class="empty">Belum ada Event. Buat Event pertama untuk mulai menggunakan profil khusus.</div>'}</div></section><section class="panel" id="eventEditor"><h3>Pengaturan Event</h3><p class="muted">Pilih tombol Atur pada sebuah event untuk mengubah frame, cetakan, dan fitur.</p></section>`;
 const notice=$('#eventNotice');
 $('#deactivateEvent').onclick=async()=>{try{await activateEvent(null);}catch(e){notice.textContent=e.message;}};
 $('#openEventArchive').onclick=()=>go('archive');
 $('#openEventArchive').onclick=()=>go('archive');
 $('#eventAdd').onclick=async()=>{const name=$('#eventNewName').value.trim();if(!name){notice.textContent='Nama event wajib diisi.';return;}const id=Array.from(crypto.getRandomValues(new Uint8Array(8))).map(x=>x.toString(16).padStart(2,'0')).join('');const config={};for(const k of eventConfigKeys)if(baseSettings[k]!==undefined)config[k]=JSON.parse(JSON.stringify(baseSettings[k]));config.frameId='';config.layoutSlots=[];config.frameLayouts={};config.driveQrLayouts={};const e={id,name,date:$('#eventNewDate').value,type:$('#eventNewType').value,config};eventStore.events.push(e);try{await window.kaca.writeEvents(eventStore);await renderEvents();await openEventEditor(id);}catch(error){eventStore.events=eventStore.events.filter(x=>x.id!==id);notice.textContent=error.message;}};
 content.querySelectorAll('[data-event-activate]').forEach(b=>b.onclick=async()=>{try{await activateEvent(b.dataset.eventActivate);}catch(e){notice.textContent=e.message;}});
 content.querySelectorAll('[data-event-edit]').forEach(b=>b.onclick=()=>openEventEditor(b.dataset.eventEdit));
 content.querySelectorAll('[data-event-delete]').forEach(b=>b.onclick=async()=>{const e=eventStore.events.find(x=>x.id===b.dataset.eventDelete);if(!e||!(await kacaConfirm('Hapus profil '+e.name+'? File foto yang sudah dibuat tidak akan dihapus.')))return;if(eventStore.activeEventId===e.id){notice.textContent='Nonaktifkan event sebelum menghapus profil.';return;}eventStore.events=eventStore.events.filter(x=>x.id!==e.id);await window.kaca.writeEvents(eventStore);await renderEvents();});
 async function openEventEditor(id){
  const e=eventStore.events.find(x=>x.id===id);if(!e)return;
  const c=e.config||{};let frames=[];const editor=$('#eventEditor');
  editor.innerHTML=`<h3>${esc(e.name)} · Pengaturan Khusus</h3><div class="form-grid"><div class="field"><label>Nama event</label><input id="evName" value="${esc(e.name)}"></div><div class="field"><label>Tanggal</label><input id="evDate" type="date" value="${esc(e.date||'')}"></div><div class="field"><label>Ukuran Cetak</label><select id="evPaper"><option>4R</option><option>2R Strip</option><option>Custom</option></select></div><div class="field"><label>Orientasi</label><select id="evOrient"><option value="portrait">Portrait</option><option value="landscape">Landscape</option></select></div><div class="field"><label>Lebar custom (inci)</label><input id="evWidth" type="number" min="1" max="20" step="0.1" value="${Number(c.customWidth||4)}"></div><div class="field"><label>Tinggi custom (inci)</label><input id="evHeight" type="number" min="1" max="20" step="0.1" value="${Number(c.customHeight||6)}"></div><div class="field"><label>Jumlah salinan cetak</label><input id="evCopies" type="number" min="1" max="9" value="${Number(c.printCopies||1)}"></div></div><div class="event-features"><label class="frame-enable-check"><input type="checkbox" id="evPhoto" ${c.enablePhotoMode!==false?'checked':''}> Aktifkan PHOTO</label><label class="frame-enable-check"><input type="checkbox" id="evVideo" ${c.enableVideoMode!==false?'checked':''}> Aktifkan VIDEO</label><label class="frame-enable-check"><input type="checkbox" id="evLive" ${c.livePhotoEnabled!==false?'checked':''}> Live Photo saat sesi PHOTO</label></div><h3>Frame Khusus Event</h3><p class="muted">PNG transparan yang diunggah di sini hanya tersedia untuk event ini. Atur posisi slot di menu Frame & Layout setelah mengaktifkan event.</p><div class="form-grid"><div class="field"><label>Upload Frame PNG</label><input type="file" id="evFrameUpload" accept="image/png"></div><div class="field"><label>Pilih Frame Utama Event</label><select id="evFrame"><option value="">Pilih frame event</option></select></div></div><div id="evFrameGallery" class="event-frame-gallery"></div><div class="actions wrap"><button class="btn secondary" id="evUpload">Unggah Frame Event</button><button class="btn" id="evSave">Simpan Pengaturan Event</button><button class="btn secondary" id="evActivate">Aktifkan Event Ini</button></div><div class="notice" id="evStatus">Pengaturan event siap diubah.</div>`;
  const el=id=>$('#'+id);el('evPaper').value=c.paperSize||'4R';el('evOrient').value=c.orientation||'portrait';
  const refreshFrames=async()=>{try{const r=await api('/api/frames');frames=(r.frames||[]).filter(f=>f.event_id===e.id);el('evFrame').innerHTML='<option value="">Pilih frame event</option>'+frames.map(f=>`<option value="${esc(f.id)}">${esc(f.name)}</option>`).join('');el('evFrame').value=frames.some(f=>f.id===c.frameId)?c.frameId:'';el('evFrameGallery').innerHTML=frames.length?frames.map(f=>`<figure><img src="${f.url}" alt="${esc(f.name)}"><figcaption>${esc(f.name)}</figcaption></figure>`).join(''):'<p class="muted">Belum ada frame untuk event ini.</p>';}catch(error){el('evStatus').textContent='Tidak dapat memuat frame: '+error.message;}};
  await refreshFrames();
  el('evUpload').onclick=async()=>{const file=el('evFrameUpload').files[0];if(!file){el('evStatus').textContent='Pilih PNG transparan terlebih dahulu.';return;}if(file.size>15*1024*1024){el('evStatus').textContent='Ukuran file maksimal 15 MB.';return;}try{el('evUpload').disabled=true;const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file);});const r=await api('/api/frames/import',{method:'POST',body:JSON.stringify({name:file.name,data_url:data,event_id:e.id})});c.frameId=r.frame.id;e.config=c;await window.kaca.writeEvents(eventStore);await refreshFrames();el('evStatus').textContent='Frame event berhasil diunggah.';}catch(error){el('evStatus').textContent='Gagal mengunggah: '+error.message;}finally{el('evUpload').disabled=false;}};
  el('evSave').onclick=async()=>{try{if(!el('evPhoto').checked&&!el('evVideo').checked)throw new Error('Aktifkan minimal PHOTO atau VIDEO.');e.name=el('evName').value.trim().slice(0,100);if(!e.name)throw new Error('Nama event tidak boleh kosong.');e.date=el('evDate').value;c.paperSize=el('evPaper').value;c.orientation=el('evOrient').value;c.customWidth=Math.max(1,Math.min(20,Number(el('evWidth').value)||4));c.customHeight=Math.max(1,Math.min(20,Number(el('evHeight').value)||6));c.printCopies=Math.max(1,Math.min(9,Number(el('evCopies').value)||1));c.enablePhotoMode=el('evPhoto').checked;c.enableVideoMode=el('evVideo').checked;c.livePhotoEnabled=el('evLive').checked;c.frameId=el('evFrame').value||'';e.config=c;await window.kaca.writeEvents(eventStore);if(activeEvent()?.id===e.id)settings=effectiveSettings();el('evStatus').textContent='Konfigurasi berhasil disimpan. Pengaturan umum tidak berubah.';}catch(error){el('evStatus').textContent=error.message;}};
  el('evActivate').onclick=async()=>{await el('evSave').onclick();if(el('evStatus').textContent.startsWith('Konfigurasi berhasil'))await activateEvent(e.id);};
 }
}

async function renderLicense(){
 const el=$('#content'),state=await window.kaca.cloudStatus();
 const until=state.licenseExpires?new Date(state.licenseExpires*1000).toLocaleString('id-ID'):'—';
 el.innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / LISENSI</div><h2>Aktivasi Akun & Lisensi</h2><p class="muted">Aktivasi pertama memerlukan internet. Setelah aktif, sesi foto dan video tetap dapat digunakan offline sampai tanggal kedaluwarsa lisensi digital.</p><div class="notice" id="licenseStatus">${state.licenseActive?'Lisensi aktif untuk '+esc(state.boothName)+' hingga '+esc(until):'Belum aktif / kedaluwarsa: '+esc(state.lastError||'Masukkan lisensi resmi.')}</div><div class="form-grid"><div class="field"><label>Server Cloud</label><input id="licenseServer" type="url" value="${esc(state.server||'https://kacastudio.id')}"></div><div class="field"><label>Nama Booth</label><input id="licenseBooth" value="${esc(state.boothName||'')}"></div><div class="field"><label>Email Akun</label><input id="licenseEmail" type="email" autocomplete="email"></div><div class="field"><label>Password</label><input id="licensePassword" type="password" autocomplete="current-password"></div><div class="field"><label>Kode Lisensi</label><input id="licenseCode" type="text" autocomplete="off" placeholder="KACA-XXXXXXXX-XXXXXXXXXX"></div></div><div class="actions wrap"><button class="btn" id="licenseActivate">Aktifkan Lisensi</button><button class="btn secondary" id="licenseRefresh">Periksa Lisensi Offline</button><button class="btn secondary" id="licensePackages">Lihat Paket & Harga</button></div><p class="muted">Lisensi ditandatangani oleh Cloud dan terikat pada perangkat ini. Perubahan tanggal komputer yang tidak wajar dapat membuat pemeriksaan offline ditolak.</p></div>`;
 $('#licenseActivate').onclick=async()=>{
   const button=$('#licenseActivate'),status=$('#licenseStatus');button.disabled=true;
   try{
     const data={server:$('#licenseServer').value.trim(),boothName:$('#licenseBooth').value.trim(),email:$('#licenseEmail').value.trim(),password:$('#licensePassword').value,licenseCode:$('#licenseCode').value.trim()};
     const r=await window.kaca.activateCloudLicense(data);
     status.textContent=r.licenseActive?'Lisensi berhasil diaktifkan. Berlaku sampai '+new Date(r.licenseExpires*1000).toLocaleString('id-ID'):'Aktivasi belum valid.';
     $('#licensePassword').value='';$('#licenseCode').value='';
   }catch(e){status.textContent='Aktivasi gagal: '+e.message;}finally{button.disabled=false;}
 };
 $('#licenseRefresh').onclick=()=>renderLicense();
 $('#licensePackages').onclick=()=>window.kaca.openExternal('https://kacastudio.id/paket');
}
async function renderCloudControl(){
 const el=$('#content');
 const state=await window.kaca.cloudStatus();
 el.innerHTML=`<div class="panel"><div class="eyebrow2">KACA.ID / CLOUD CONTROL</div><h2>Cloud Account & Lisensi Multi Booth</h2><p class="muted">Aktivasi online hanya diperlukan pertama kali. Setelah lisensi digital aktif, KACA.ID tetap berfungsi tanpa internet dan menyinkronkan sesi secara otomatis ketika terhubung kembali.</p><div class="notice" id="cloudConnectionState">—</div><div class="form-grid"><div class="field"><label>Nama Booth</label><input id="cloudBoothName" disabled></div><div class="field"><label>Server Cloud</label><input id="cloudServerName" disabled></div></div><div class="actions"><button class="btn" id="cloudActivateButton">Aktivasi Akun / Lisensi</button><button class="btn secondary" id="cloudSyncButton">Sinkronkan Sekarang</button><button class="btn secondary" id="cloudRemoteStop">Cabut Izin Remote</button></div><label style="display:flex;gap:9px;align-items:center;margin-top:20px"><input type="checkbox" id="cloudThumbConsent"> Izinkan unggah thumbnail foto ke Cloud (opsional)</label><p class="muted">Lisensi hanya dibuat Super Admin. Setiap kode digunakan untuk satu booth; satu akun boleh mempunyai beberapa booth. Remote layar hanya tersedia setelah operator setempat mengizinkan.</p></div>`;
 const refresh=async()=>{const s=await window.kaca.cloudStatus();const license=s.licenseActive?`Lisensi aktif · ID ${s.boothId} · hingga ${new Date(s.licenseExpires*1000).toLocaleDateString('id-ID')}`:'Lisensi belum aktif atau sudah berakhir';const sync=s.connected?'Cloud tersambung':`Cloud offline / belum sinkron${s.lastSync?' · terakhir '+new Date(s.lastSync).toLocaleString('id-ID'):''}`;$('#cloudConnectionState').textContent=`${license} · ${sync}${s.lastError?' · '+s.lastError:''}`;$('#cloudBoothName').value=s.boothName||'';$('#cloudServerName').value=s.server||'';$('#cloudThumbConsent').checked=s.shareThumbnails};
 $('#cloudActivateButton').onclick=async()=>{try{await window.kaca.openCloudActivation();await refresh();}catch(e){$('#cloudConnectionState').textContent=e.message}};
 $('#cloudSyncButton').onclick=async()=>{try{const s=await window.kaca.syncCloudNow();await refresh();if(s.lastError)$('#cloudConnectionState').textContent='Sinkronisasi belum berhasil: '+s.lastError;else if(s.connected)$('#cloudConnectionState').textContent='Sinkronisasi Cloud berhasil · '+new Date(s.lastSync).toLocaleString('id-ID');else $('#cloudConnectionState').textContent='Sinkronisasi diminta, tetapi Cloud belum mengonfirmasi.';}catch(e){$('#cloudConnectionState').textContent='Sinkronisasi gagal: '+e.message}};
 $('#cloudRemoteStop').onclick=async()=>{await window.kaca.stopCloudRemote();await refresh()};
 $('#cloudThumbConsent').onchange=async e=>{await window.kaca.cloudShareThumbnails(e.target.checked);await refresh()};
}
let navigationGeneration=0;
async function renderKacaMenuOnce(page){if(window.kacaCurrentMenu==='generalSettings'&&page!=='generalSettings')window.kacaCameraPreviewStop?.();const pageGeneration=++navigationGeneration;window.kacaCurrentMenu=page;document.body.classList.toggle('dashboard-mode',page==='dashboard');document.body.classList.toggle('photo-session-mode',page==='capture'||page==='videoCapture');document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));$('#pageTitle').textContent=titles[page]||'Dashboard';$('#content').innerHTML=`<div class="panel menu-loading-state"><h3>Memuat ${esc(titles[page]||page)}…</h3><p class="muted">Menyiapkan data pengaturan. Menu tetap tersedia meskipun perangkat eksternal sedang tidak terhubung.</p></div>`;try{if(activeEvent()&&((page==='capture'&&settings.enablePhotoMode===false)||(page==='videoCapture'&&settings.enableVideoMode===false))){$('#content').innerHTML=`<div class="panel"><h3>Fitur tidak aktif pada event ini</h3><p class="muted">Aktifkan fitur melalui Manajemen Event sebelum memulai sesi.</p><button type="button" class="btn" id="openEventSettings">Manajemen Event</button></div>`;$('#openEventSettings').onclick=()=>go('events');return;}if(page==='dashboard'){$('#content').innerHTML=dashboard();$('#adminHome').onclick=openAdminPin;if($('#startPhotoSession'))$('#startPhotoSession').onclick=()=>go('capture');if($('#startVideoSession'))$('#startVideoSession').onclick=()=>go('videoCapture');initDashboardPreview();return;}else if(page==='appearance'){await renderAppearance();return;}else if(page==='generalSettings'){await renderGeneralSettings();return;}else if(page==='events'){await renderEvents();return;}else if(page==='cloudControl'){await renderCloudControl();return;}else if(page==='license'){await renderLicense();return;}else if(page==='devices'){renderDevices();return;}else if(page==='printers'){await renderPrinters();return;}else if(page==='capture'){await renderCapture();}else if(page==='videoCapture'){await renderVideoCapture();}else if(page==='sessionSettings'){await renderSessionSettings();}else if(page==='frames'){await renderFrames();}else if(page==='filters'){await renderFilters();}else if(page==='archive'||page==='output'){await renderSessions(page);}else if(page==='voucher'){await renderVoucherAdmin();}else if(page==='payment'){await renderPaymentSettings();}else $('#content').innerHTML=renderForm(page);document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));const save=$('#save');if(save)save.onclick=async()=>{document.querySelectorAll('[data-key]').forEach(el=>settings[el.dataset.key]=el.value);await saveScopedSettings();save.textContent='Tersimpan ✓';setTimeout(()=>save.textContent='Simpan Pengaturan',1600);};const reset=$('#reset');if(reset)reset.onclick=()=>go(page);if(pageGeneration===navigationGeneration&&!$('#content').textContent.trim())throw new Error('Halaman tidak mengembalikan konten.');}catch(error){if(pageGeneration!==navigationGeneration)return;console.error('[KACA_SETTINGS_MENU]',page,error);$('#content').innerHTML=`<div class="panel menu-error-state"><h3>Menu ${esc(titles[page]||page)} gagal dimuat</h3><p>${esc(error?.message||String(error))}</p><p class="muted">Periksa koneksi backend, lalu coba memuat menu ini kembali. Data tersimpan tidak berubah.</p><button id="retryMenu" class="btn">Coba Muat Ulang</button><button id="menuBack" class="btn secondary">Dashboard</button></div>`;$('#retryMenu').onclick=()=>go(page);$('#menuBack').onclick=()=>go('dashboard');}}
// v0.9.84 — bounded structural menu self-healing.
// A non-empty page is NOT necessarily a complete page. Each admin page has a
// minimal contract of controls that must exist (hidden submenu controls count).
// Never automatically reload an active PHOTO/VIDEO session or erase a form the
// operator is editing. Avoid unbounded retries when a backend is offline.
let kacaMenuRequest=0,kacaMenuWatchTimer=null,kacaMenuAutoHealing=false,kacaMenuUserEdited=false;
const kacaMenuContracts={
 dashboard:['.studio-dashboard','.dash-brand h1','.dash-camera-card','#adminHome'],
 appearance:['#dashTitleInput','#chooseDashLogo','#saveDashAppearance','#uiDesignerStage'],
 generalSettings:['.kaca-general-tabs','[data-settings-tab="storage"]','[data-settings-tab="sharing"]','[data-settings-tab="camera"]','[data-settings-tab="logs"]','#saveLocalStorage','#googleDriveStatus','#waDeliveryMode','#fonnteGatewayStatus','#multiCamera1','#appLogsViewer'],
 events:['#eventAdd','#eventEditor','#eventNewName'],
 frames:['#saveLayout','#savedFrames','#layoutEditorPreview','#slotPreviewLayer'],
 filters:['#saveFilter','#filterStatus'],
 output:['#sessionList','#retentionStatus','#saveRetention'],
 archive:['#sessionList'],
 voucher:['#voucherTable','#generateVouchers','#voucherAdminStatus'],
 payment:['#savePaymentMethods','#qrisIntegrationMode','#saveDokuGateway'],
 devices:['#cameras','#camStatus','#scan'],
 printers:['#printerSelect','#savePrinterSettings','#printerStatus'],
 sessionSettings:['#additionalPrintEnabled','#autoPrintEnabled'],
 setup:['#save'],license:['#licenseStatus','#licenseServer','#licenseBooth','#licenseEmail','#licensePassword','#licenseCode','#licenseActivate','#licenseRefresh','#licensePackages']
};
function kacaMenuHealth(page){
 const content=$('#content');
 if(!content)return {ok:false,reason:'Kontainer halaman tidak tersedia.'};
 if(content.querySelector('.menu-error-state'))return {ok:false,reason:content.querySelector('.menu-error-state').innerText.slice(0,320)};
 if(content.querySelector('.menu-loading-state'))return {ok:false,reason:'Halaman masih dalam proses pemuatan.'};
 const expected=kacaMenuContracts[page];
 if(!expected)return {ok:!!content.innerText.trim(),reason:'Halaman belum memiliki konten.'};
 const missing=expected.filter(selector=>!content.querySelector(selector));
 if(missing.length)return {ok:false,reason:'Bagian pengaturan belum tersedia: '+missing.join(', ')};
 const rootBox=content.getBoundingClientRect();
 if(rootBox.width<80||rootBox.height<30)return {ok:false,reason:'Area halaman tidak mempunyai ukuran tampilan yang valid.'};
 if(page==='generalSettings'){
  const nav=content.querySelector('.kaca-general-tabs');
  const active=nav?.querySelector('[data-settings-tab][aria-pressed="true"]');
  const group=active?.dataset.settingsTab;
  if(!group)return {ok:false,reason:'Submenu Pengaturan Umum belum dipilih.'};
  // Validate that the selected section is really visible, not just present
  // in the DOM but hidden by a stylesheet or an incomplete tab transition.
  const visible=Array.from(content.querySelectorAll('.panel')).some(panel=>{
   if(panel.hidden||getComputedStyle(panel).display==='none')return false;
   const part=Array.from(panel.querySelectorAll(':scope > .kaca-general-subsection')).filter(section=>section.dataset.settingsGroup===group&&!section.hidden&&getComputedStyle(section).display!=='none');
   return (part.length>0||panel.dataset.settingsGroup===group)&&panel.getBoundingClientRect().height>30;
  });
  if(!visible)return {ok:false,reason:'Submenu '+group+' belum tampil secara utuh.'};
 }
 return {ok:true,reason:''};
}
const kacaMenuSleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function kacaCheckAfterPaint(){
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 await kacaMenuSleep(110);
}
function kacaShowMenuRecovery(page,reason){
 const target=$('#content');if(!target)return;
 try{window.kaca?.reportRendererError?.({level:'menu-render-incomplete',message:`${page}: ${reason}`});}catch{}
 // Do not erase a partially loaded menu where user-entered values may exist.
 // Add a clear recovery surface instead.
 let panel=target.querySelector('#kacaMenuIntegrityError');
 if(!panel){panel=document.createElement('section');panel.id='kacaMenuIntegrityError';panel.className='panel menu-error-state kaca-menu-integrity-error';target.prepend(panel);}
 panel.innerHTML=`<h3>Menu ${esc(titles[page]||page)} belum tampil lengkap</h3><p>${esc(reason)}</p><p class="muted">Aplikasi telah mencoba memuat ulang beberapa kali. Anda dapat mencoba lagi tanpa menutup KACA.ID.</p><div class="actions"><button type="button" class="btn" id="kacaIntegrityRetry">Coba Muat Ulang</button><button type="button" class="btn secondary" id="kacaIntegrityDashboard">Dashboard</button></div>`;
 panel.querySelector('#kacaIntegrityRetry').onclick=()=>void go(page);
 panel.querySelector('#kacaIntegrityDashboard').onclick=()=>void go('dashboard');
}
function kacaWatchMenu(page,request,autoRecovered){
 if(kacaMenuWatchTimer){clearInterval(kacaMenuWatchTimer);kacaMenuWatchTimer=null;}
 if(page==='capture'||page==='videoCapture'||autoRecovered)return;
 const started=Date.now();
 kacaMenuWatchTimer=setInterval(()=>{
  if(request!==kacaMenuRequest||window.kacaCurrentMenu!==page||Date.now()-started>5500||document.body.classList.contains('photo-session-mode')){
   clearInterval(kacaMenuWatchTimer);kacaMenuWatchTimer=null;return;
  }
  const health=kacaMenuHealth(page);
  if(health.ok)return;
  clearInterval(kacaMenuWatchTimer);kacaMenuWatchTimer=null;
  if(kacaMenuUserEdited){kacaShowMenuRecovery(page,health.reason);return;}
  console.warn('[KACA_MENU_LATE_INCOMPLETE]',page,health.reason);
  void go(page,{autoRecovered:true});
 },950);
}
async function go(page,{autoRecovered=false}={}){
 const request=++kacaMenuRequest;
 kacaMenuUserEdited=false;
 if(kacaMenuWatchTimer){clearInterval(kacaMenuWatchTimer);kacaMenuWatchTimer=null;}
 // Customer sessions have their own lifecycle; never re-create them automatically.
 if(page==='capture'||page==='videoCapture'){
   try{await window.kaca.assertCloudLicense();}
   catch(e){
     await renderKacaMenuOnce('license');
     const msg=$('#licenseStatus');if(msg)msg.textContent='Sesi terkunci: '+e.message+' Aktifkan lisensi untuk membuka PHOTO/VIDEO.';
     return false;
   }
   return renderKacaMenuOnce(page);
 }
 let lastFailure='';
 for(let attempt=0;attempt<3;attempt++){
  if(request!==kacaMenuRequest)return false;
  try{await renderKacaMenuOnce(page);}catch(err){lastFailure=err?.message||String(err);}
  if(request!==kacaMenuRequest)return false;
  await kacaCheckAfterPaint();
  if(request!==kacaMenuRequest)return false;
  const status=kacaMenuHealth(page);
  if(status.ok){
   if(attempt)console.info('[KACA_MENU_RECOVERED]',page,'percobaan',attempt+1);
   kacaWatchMenu(page,request,autoRecovered);
   return true;
  }
  lastFailure=status.reason||lastFailure;
  console.warn('[KACA_MENU_INCOMPLETE]',page,attempt+1,lastFailure);
  if(kacaMenuUserEdited)break;
  if(attempt<2)await kacaMenuSleep(260*(attempt+1));
 }
 if(request===kacaMenuRequest)kacaShowMenuRecovery(page,lastFailure||'Komponen tidak lengkap setelah pemuatan ulang.');
 return false;
}
document.addEventListener('input',e=>{
 if(e.target?.closest?.('#content')&&e.isTrusted)kacaMenuUserEdited=true;
},true);

// v0.9.82: self-healing menu navigation without quitting Electron.
async function recoverKacaMenu(){
 if(document.body.classList.contains('photo-session-mode')){
  const notice=$('#flowSessionStatus')||$('#flowFrameStatus');if(notice)notice.textContent='Jangan memulihkan navigasi saat sesi PHOTO/VIDEO aktif. Selesaikan sesi terlebih dahulu.';
  return;
 }
 document.querySelectorAll('.admin-pin-overlay,.session-pin-overlay,.kaca-share-overlay,.session-detail-overlay').forEach(x=>x.remove());
 if(typeof closeKacaKeyboard==='function')closeKacaKeyboard();
 const current=window.kacaCurrentMenu||'dashboard';
 const destination=current==='capture'||current==='videoCapture'?'dashboard':current;
 try{await go(destination);}
 catch(err){console.error('[KACA_MENU_RECOVER]',err);const body=$('#content');if(body)body.innerHTML=`<div class="panel menu-error-state"><h3>Menu belum pulih</h3><p>${esc(err.message||String(err))}</p><button class="btn" id="fallbackDashboard">Buka Dashboard</button></div>`;if($('#fallbackDashboard'))$('#fallbackDashboard').onclick=()=>go('dashboard');}
}
const recoveryButton=document.getElementById('kacaRecoverMenu');
if(recoveryButton)recoveryButton.onclick=()=>void recoverKacaMenu();
let kacaMenuLoadingSince=0;
setInterval(()=>{
 if(document.body.classList.contains('kaca-booting')||document.body.classList.contains('photo-session-mode'))return;
 const content=$('#content');if(!content)return;
 const pending=!!content.querySelector('.menu-loading-state');
 if(!pending){kacaMenuLoadingSince=0;return;}
 if(!kacaMenuLoadingSince)kacaMenuLoadingSince=Date.now();
 if(Date.now()-kacaMenuLoadingSince>12000){
  const panel=content.querySelector('.menu-loading-state');
  if(panel&&!panel.querySelector('[data-menu-try]')){
   const btn=document.createElement('button');btn.className='btn secondary';btn.type='button';btn.dataset.menuTry='1';btn.textContent='Menu terlalu lama — Coba Muat Ulang';btn.onclick=()=>void recoverKacaMenu();panel.appendChild(btn);
  }
 }
},2500);
// Ctrl+Alt+R reloads only the renderer from Electron, useful if the UI thread freezes.
// On-screen numeric keyboard for PIN and customer WhatsApp fields (touch-screen booths).
let kacaKeyboardTarget=null;
function closeKacaKeyboard(){const k=document.getElementById('kacaVirtualKeyboard');if(k)k.hidden=true;kacaKeyboardTarget=null;}
function showKacaKeyboard(input){kacaKeyboardTarget=input;let k=document.getElementById('kacaVirtualKeyboard');if(!k){k=document.createElement('div');k.id='kacaVirtualKeyboard';k.className='kaca-virtual-keyboard';k.hidden=true;k.innerHTML='<div class="vk-head"><b>Keyboard</b><button type="button" data-vk-close>×</button></div><div class="vk-keys">'+['1','2','3','4','5','6','7','8','9','+','0','⌫','Hapus','Selesai'].map(v=>`<button type="button" data-vk-key="${v}">${v}</button>`).join('')+'</div>';document.body.appendChild(k);k.addEventListener('pointerdown',e=>{if(e.target.closest('button'))e.preventDefault();});k.addEventListener('click',e=>{const b=e.target.closest('[data-vk-key]');if(e.target.closest('[data-vk-close]')){closeKacaKeyboard();return;}if(!b||!kacaKeyboardTarget)return;const input=kacaKeyboardTarget,key=b.dataset.vkKey;if(key==='+'&&input.inputMode!=='tel')return;const start=input.selectionStart??input.value.length,end=input.selectionEnd??start;if(key==='Selesai'){closeKacaKeyboard();input.blur();return;}if(key==='Hapus'){input.value='';}else if(key==='⌫'){input.value=input.value.slice(0,Math.max(0,start-1))+input.value.slice(end);input.setSelectionRange(Math.max(0,start-1),Math.max(0,start-1));}else{const next=input.value.slice(0,start)+key+input.value.slice(end);input.value=input.maxLength>0?next.slice(0,input.maxLength):next;input.setSelectionRange(start+key.length,start+key.length);}input.dispatchEvent(new Event('input',{bubbles:true}));});}k.hidden=false;}
document.addEventListener('focusin',e=>{const el=e.target;if(el instanceof HTMLInputElement&&(el.inputMode==='numeric'||el.inputMode==='tel'||el.type==='password'&&el.inputMode==='numeric'))showKacaKeyboard(el);});document.addEventListener('pointerdown',e=>{const k=document.getElementById('kacaVirtualKeyboard');if(k&&!k.contains(e.target)&&!(e.target instanceof HTMLInputElement&&e.target===kacaKeyboardTarget))closeKacaKeyboard();});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeKacaKeyboard();});
window.addEventListener('error',e=>{try{window.kaca.reportRendererError({level:'renderer-error',message:`${e.message||'Unknown error'} at ${e.filename||''}:${e.lineno||0}:${e.colno||0} ${e.error?.stack||''}`});}catch{}});
window.addEventListener('unhandledrejection',e=>{try{const r=e.reason;window.kaca.reportRendererError({level:'renderer-rejection',message:r?.stack||r?.message||String(r)});}catch{}});
document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click',()=>go(b.dataset.page)));
const startupScreen=$('#kacaStartupScreen'),startupMessage=$('#kacaStartupText'),startupProgress=$('#kacaStartupProgress'),startupRecovery=$('#kacaStartupRecovery');
const startupStatus=(message,progress)=>{if(startupMessage)startupMessage.textContent=message;if(startupProgress)startupProgress.style.width=Math.max(5,Math.min(100,progress))+'%';};
const delayStartup=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const waitForCameraService=async()=>{
 const deadline=Date.now()+26000;
 while(Date.now()<deadline){
  startupStatus('Memeriksa koneksi backend kamera dan penyimpanan…',64);
  const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),1750);
  try{
   const response=await fetch('http://127.0.0.1:8765/health',{cache:'no-store',signal:ctrl.signal});
   if(response.ok){const body=await response.json();if(body.ok===true&&(!body.app_version||body.app_version===$('#version').textContent.replace(/^v/,'')))return true;}
  }catch(e){console.debug('[KACA_BOOT_SERVICE_WAIT]',e?.message||String(e));}
  finally{clearTimeout(timer);}
  await delayStartup(500);
 }
 throw new Error('Backend kamera belum siap. Periksa proses Python, konfigurasi kamera, atau instalasi runtime.');
};
const waitDashboardMedia=async()=>{
 const video=$('.studio-dashboard .dash-background'),image=$('.studio-dashboard .dash-background-image');
 const media=video||image;
 if(!media || (video?media.readyState>=2:media.complete&&media.naturalWidth>0))return;
 await Promise.race([new Promise(resolve=>{
  const event=video?'loadeddata':'load';media.addEventListener(event,resolve,{once:true});media.addEventListener('error',resolve,{once:true});
 }),delayStartup(2500)]);
};
let startupBusy=false;
const showDashboardFromStartup=async(offline=false)=>{
 startupStatus('Menyiapkan tampilan Dashboard utama…',89);
 await go('dashboard');
 if(!$('.studio-dashboard'))throw new Error('Dashboard belum berhasil ditampilkan.');
 await waitDashboardMedia();
 startupStatus(offline?'Dashboard terbuka (kamera dapat dihubungkan dari Pengaturan Perangkat).':'Dashboard siap digunakan.',100);
 document.body.classList.remove('kaca-booting');
 if(startupScreen)startupScreen.hidden=true;
};
const bootKaca=async(offline=false)=>{
 if(startupBusy)return;
 startupBusy=true;
 if(startupRecovery)startupRecovery.hidden=true;
 try{
  startupStatus('Memuat pengaturan booth dan konfigurasi Event…',20);
  baseSettings=await window.kaca.readSettings()||{};
  if(!baseSettings||typeof baseSettings!=='object')throw new Error('Format pengaturan aplikasi tidak valid.');
  startupStatus('Memulihkan profil Event dan konfigurasi tampilan…',43);
  eventStore=await window.kaca.readEvents()||{activeEventId:null,events:[]};
  if(!Array.isArray(eventStore.events))eventStore={activeEventId:null,events:[]};
  settings=effectiveSettings();applyAppTheme();
  $('#version').textContent='v'+await window.kaca.version();
  if(!offline)await waitForCameraService();
  await showDashboardFromStartup(offline);
 }catch(err){
  console.error('[KACA_BOOT_FAILED]',err);
  startupStatus('Inisialisasi belum berhasil.',65);
  if($('#kacaStartupError'))$('#kacaStartupError').textContent=err?.message||String(err);
  if(startupRecovery)startupRecovery.hidden=false;
 }finally{startupBusy=false;}
};
if($('#kacaStartupRetry'))$('#kacaStartupRetry').onclick=()=>bootKaca();
if($('#kacaStartupOffline'))$('#kacaStartupOffline').onclick=()=>bootKaca(true);

// Cloud updates never force a reload during an active photo/video session.
window.kaca.onCloudSettingsUpdated?.(async()=>{if(['capture','videoCapture'].includes(window.kacaCurrentMenu))return;
 try{baseSettings=await window.kaca.readSettings();settings=effectiveSettings();applyAppTheme();await go('dashboard')}catch(e){console.warn('[KACA_CLOUD_SETTINGS_REFRESH]',e)}});
window.kaca.onCloudDashboard?.(()=>{if(!['capture','videoCapture'].includes(window.kacaCurrentMenu))void go('dashboard')});
void bootKaca();
