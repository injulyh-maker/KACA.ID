from pathlib import Path
p=Path('/mnt/data/kaca_v0943_work/backend/camera_server.py')
s=p.read_text(encoding='utf-8')
old='''def _render_session_worker(session_id):
    """Render still/frame, framed Live Photo and GIF off the customer UI thread."""
'''
new='''def _cleanup_session_live_sources(snapshot):
    """Remove per-shot Live Photo inputs only after the final render is committed."""
    session_dir=os.path.join(SESSIONS_DIR, snapshot.get('id',''))
    for shot in snapshot.get('photos', []):
        clip=shot.get('live_photo')
        preview_clip=shot.get('live_photo_preview')
        for temporary_clip in (clip, preview_clip):
            if temporary_clip:
                try: os.remove(os.path.join(session_dir, temporary_clip))
                except OSError: pass
        if clip or preview_clip:
            shot['live_photo']=None
            shot['live_photo_preview']=None
            shot['live_photo_url']=None
            shot['live_photo_preview_url']=None


def _render_session_worker(session_id):
    """Render still/frame and framed Live Photo; keep source clips during filter review."""
'''
assert old in s
s=s.replace(old,new,1)
old='''            gif_file=None
            # Per-shot source clips are temporary inputs only. Keep only the single
            # composed Live Photo with the selected frame; retain full-quality still JPGs.
            for shot in snapshot.get('photos', []):
                clip=shot.get('live_photo')
                preview_clip=shot.get('live_photo_preview')
                for temporary_clip in (clip, preview_clip):
                    if temporary_clip:
                        try: os.remove(os.path.join(SESSIONS_DIR, session_id, temporary_clip))
                        except OSError: pass
                if clip or preview_clip:
                    shot['live_photo']=None
                    shot['live_photo_preview']=None
                    shot['live_photo_url']=None
                    shot['live_photo_preview_url']=None
            snapshot['live_output']=live_output
'''
new='''            gif_file=None
            # Keep per-shot source clips while the customer is still on the filter
            # slide: changing the filter or selected photos must be renderable again.
            snapshot['live_output']=live_output
'''
assert old in s
s=s.replace(old,new,1)
old='''                finish_requested=bool(job.get('finish_requested'))
                snapshot['status']='finished' if finish_requested else 'processing'
                if finish_requested:
                    snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds')
                enqueue_local_session_archive(snapshot, final=finish_requested)
'''
new='''                finish_requested=bool(job.get('finish_requested'))
                if finish_requested:
                    _cleanup_session_live_sources(snapshot)
                snapshot['status']='finished' if finish_requested else 'processing'
                if finish_requested:
                    snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds')
                enqueue_local_session_archive(snapshot, final=finish_requested)
'''
assert old in s
s=s.replace(old,new,1)
old='''            if finish_requested and same_request and job.get('ready'):
                snapshot=job['session']
                snapshot['status']='finished'; snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds'); snapshot['render_status']='ready'
                enqueue_local_session_archive(snapshot, final=True)
'''
new='''            if finish_requested and same_request and job.get('ready'):
                snapshot=job['session']
                _cleanup_session_live_sources(snapshot)
                snapshot['status']='finished'; snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds'); snapshot['render_status']='ready'
                enqueue_local_session_archive(snapshot, final=True)
'''
assert old in s
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

p=Path('/mnt/data/kaca_v0943_work/src/app.js')
s=p.read_text(encoding='utf-8')
old='''  // Rendering berat (JPG frame, Live Photo, GIF) hanya dijalankan sekali saat operator menekan tombol selesai.
  // Perubahan pilihan foto/filter cukup memperbarui canvas pratinjau di renderer agar tidak membuat antrean render backend berulang.
  const scheduleBackgroundRender=()=>{};
'''
new='''  // Siapkan JPG final dan Live Photo ber-frame selama pelanggan berada di slide Filter.
  // Debounce perubahan pilihan agar render tidak dimulai untuk setiap klik yang berdekatan.
  let backgroundRenderTimer=null,backgroundRenderPromise=Promise.resolve(),backgroundRenderRevision=0;
  const buildRenderPayload=()=>({selected_numbers:(selectionMode?selectedNumbers:photos.slice(0,target()).map(p=>Number(p.number))).slice(),frame_slots:target(),frame_id:settings.frameId||null,layout_slots:Array.isArray(settings.layoutSlots)?settings.layoutSlots.map(v=>({...v})):[],drive_qr_enabled:settings.driveQrEnabled===true,drive_qr_layout:settings.driveQrLayouts?.[settings.frameId]||settings.driveQrLayout||{x:.78,y:.78,w:.16,h:.16},filter:selectedFilter});
  const scheduleBackgroundRender=()=>{
   if(backgroundRenderTimer)clearTimeout(backgroundRenderTimer);
   if(!session||flowStep!==4)return;
   const payload=buildRenderPayload();if(!payload.selected_numbers.length)return;
   const revision=++backgroundRenderRevision;
   backgroundRenderTimer=setTimeout(()=>{
    backgroundRenderTimer=null;
    backgroundRenderPromise=api('/api/session/prepare',{method:'POST',body:JSON.stringify(payload)}).then(()=>{
     if(revision===backgroundRenderRevision){const note=$('#flowFilterNote');if(note)note.textContent=`Filter ${activeFilter().name} dipilih. Hasil foto dan Live Photo sedang disiapkan di latar belakang.`;}
    }).catch(e=>{if(revision===backgroundRenderRevision){const note=$('#flowFilterNote');if(note)note.textContent='Pratinjau final belum dapat disiapkan: '+e.message;}});
   },450);
  };
  const waitForPreparedPreview=async()=>{
   if(backgroundRenderTimer){clearTimeout(backgroundRenderTimer);backgroundRenderTimer=null;}
   await backgroundRenderPromise.catch(()=>{});
   const payload=buildRenderPayload();if(!payload.selected_numbers.length)throw new Error('Pilih minimal satu foto untuk frame.');
   await api('/api/session/prepare',{method:'POST',body:JSON.stringify(payload)});
   const started=Date.now();
   while(Date.now()-started<120000){
    const state=await api(`/api/session/${session.id}/render-status`);
    if(state.render_status==='ready')return state;
    if(state.render_status==='error')throw new Error(state.render_error||'Render hasil akhir gagal.');
    const note=$('#flowFilterNote');if(note)note.textContent='Menyiapkan foto final dan Live Photo dalam frame…';
    await new Promise(resolve=>setTimeout(resolve,350));
   }
   throw new Error('Persiapan preview melebihi 120 detik. Periksa kapasitas komputer atau file Live Photo.');
  };
'''
assert old in s
s=s.replace(old,new,1)
old=""" $('#flowFilterNext').onclick=async()=>{if(mode==='timed'&&!selectionMode){await enterSelection('Pilih foto terbaik untuk hasil akhir.');setFlowStep(4);return;}if(!photos.length){status.textContent='Belum ada foto dalam sesi.';return;}await drawFilterReview();await finish.onclick();};"""
new=""" $('#flowFilterNext').onclick=async()=>{if(mode==='timed'&&!selectionMode){await enterSelection('Pilih foto terbaik untuk hasil akhir.');setFlowStep(4);return;}if(!photos.length){status.textContent='Belum ada foto dalam sesi.';return;}const btn=$('#flowFilterNext');try{btn.disabled=true;btn.textContent='MENYIAPKAN HASIL…';await drawFilterReview();await waitForPreparedPreview();btn.textContent='MEMBUKA HASIL…';await finish.onclick();}catch(e){const note=$('#flowFilterNote');if(note)note.textContent='Gagal menyiapkan preview final: '+e.message;btn.textContent='COBA LAGI';}finally{btn.disabled=false;if(btn.textContent!=='COBA LAGI')btn.textContent='LANJUT KE HASIL';}};"""
assert old in s
s=s.replace(old,new,1)
# Result preview must not wait for local archive copy or Google Drive upload.
old="""if((st.render_status==='ready'||st.status==='finished')&&st.local_archive_status==='ready'){const statusEl=$('#resultRenderStatus');if(st.drive_status==='ready'&&st.drive_url){driveShareUrl=st.drive_url;if(statusEl)statusEl.innerHTML=`Hasil tersimpan lokal dan Google Drive. <a href=\"${esc(st.drive_url)}\" target=\"_blank\" rel=\"noreferrer\">Buka folder Google Drive</a>${st.drive_share_warning?' · Tautan mungkin dibatasi: '+esc(st.drive_share_warning):''}`;}else if(statusEl)statusEl.textContent=`Hasil tersimpan lokal. Status Google Drive: ${st.drive_status||'menunggu'}${st.drive_error?' · '+st.drive_error:''}`;const img=$('#resultFrameImage');if(img)img.src=`${base}/output.jpg?v=${Date.now()}`;const liveVideo=$('#resultLiveVideo');if(liveVideo&&st.live_output_preview){const liveUrl=`${base}/${encodeURIComponent(st.live_output_preview)}`;if(!liveVideo.src||!liveVideo.src.startsWith(liveUrl)){liveVideo.src=liveUrl+'?v='+Date.now();liveVideo.load();}liveVideo.hidden=false;const stillImage=$('#resultFrameImage');if(stillImage)stillImage.hidden=true;const caption=document.querySelector('.result-preview-caption');if(caption)caption.textContent='LIVE PHOTO DALAM FRAME';liveVideo.play().catch(()=>{const note=$('#resultRenderStatus');if(note)note.textContent+=' · Pemutaran otomatis menunggu browser mengizinkan playback.';});}if(st.drive_status==='ready'){clearInterval(renderPoll);}else if(st.drive_status==='local_only'&&!st.drive_url){clearInterval(renderPoll);} }else if(st.local_archive_status==='error'){const statusEl=$('#resultRenderStatus');if(statusEl)statusEl.textContent='Hasil utama tersimpan di sesi lokal, tetapi penyalinan ke folder KACA STUDIO gagal. Periksa izin folder Pictures.';clearInterval(renderPoll);}else if(st.render_status==='ready'&&st.local_archive_status!=='ready'){const statusEl=$('#resultRenderStatus');if(statusEl)statusEl.textContent='Hasil foto selesai dirender. Sedang menyalin foto, hasil frame, dan ZIP ke folder KACA STUDIO…';}else if(st.render_status==='error'){const statusEl=$('#resultRenderStatus');if(statusEl)statusEl.textContent='Render Live Photo gagal: '+(st.render_error||'kesalahan tidak diketahui');clearInterval(renderPoll);}"""
new="""if(st.render_status==='ready'||st.status==='finished'){const statusEl=$('#resultRenderStatus');if(st.local_archive_status==='error'){if(statusEl)statusEl.textContent='Preview foto dan Live Photo siap. Penyalinan ke folder KACA STUDIO gagal; hasil utama tetap tersedia di sesi lokal.';}else if(st.local_archive_status!=='ready'){if(statusEl)statusEl.textContent='Preview foto dan Live Photo siap. Sedang menyelesaikan penyimpanan lokal…';}else if(st.drive_status==='ready'&&st.drive_url){driveShareUrl=st.drive_url;if(statusEl)statusEl.innerHTML=`Hasil tersimpan lokal dan Google Drive. <a href=\"${esc(st.drive_url)}\" target=\"_blank\" rel=\"noreferrer\">Buka folder Google Drive</a>${st.drive_share_warning?' · Tautan mungkin dibatasi: '+esc(st.drive_share_warning):''}`;}else if(statusEl)statusEl.textContent=`Preview siap dan hasil tersimpan lokal. Status Google Drive: ${st.drive_status||'menunggu'}${st.drive_error?' · '+st.drive_error:''}`;const img=$('#resultFrameImage');if(img)img.src=`${base}/output.jpg?v=${Date.now()}`;const liveVideo=$('#resultLiveVideo');if(liveVideo&&st.live_output_preview){const liveUrl=`${base}/${encodeURIComponent(st.live_output_preview)}`;if(!liveVideo.src||!liveVideo.src.startsWith(liveUrl)){liveVideo.src=liveUrl+'?v='+Date.now();liveVideo.load();}liveVideo.hidden=false;const stillImage=$('#resultFrameImage');if(stillImage)stillImage.hidden=true;const caption=document.querySelector('.result-preview-caption');if(caption)caption.textContent='LIVE PHOTO DALAM FRAME';liveVideo.play().catch(()=>{const note=$('#resultRenderStatus');if(note)note.textContent+=' · Pemutaran otomatis menunggu browser mengizinkan playback.';});}if(st.drive_status==='ready'||(st.drive_status==='local_only'&&!st.drive_url)){clearInterval(renderPoll);} }else if(st.render_status==='error'){const statusEl=$('#resultRenderStatus');if(statusEl)statusEl.textContent='Render hasil foto/Live Photo gagal: '+(st.render_error||'kesalahan tidak diketahui');clearInterval(renderPoll);}else if(st.local_archive_status==='error'){const statusEl=$('#resultRenderStatus');if(statusEl)statusEl.textContent='Hasil utama tersimpan di sesi lokal, tetapi penyalinan ke folder KACA STUDIO gagal. Periksa izin folder Pictures.';}"""
assert old in s
s=s.replace(old,new,1)
# Keep background render timer from firing after leaving filter via retake.
old=""" const performRetake=async()=>{if(!session||busy||photos.length===0)return;if(completionDelayHandle){clearInterval(completionDelayHandle);completionDelayHandle=null;}selectionMode=false;"""
new=""" const performRetake=async()=>{if(!session||busy||photos.length===0)return;if(backgroundRenderTimer){clearTimeout(backgroundRenderTimer);backgroundRenderTimer=null;}backgroundRenderRevision++;if(completionDelayHandle){clearInterval(completionDelayHandle);completionDelayHandle=null;}selectionMode=false;"""
assert old in s
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
