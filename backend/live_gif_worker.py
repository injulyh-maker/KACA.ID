"""Make Live Photo GIF in a separate process to protect the camera backend."""
import sys, os, math, shutil

def main():
    source,dest,archive=sys.argv[1:4]
    import cv2
    from PIL import Image
    capture=cv2.VideoCapture(source)
    if not capture.isOpened():raise RuntimeError('Sumber video gagal dibuka.')
    tmp=dest+'.tmp.gif'
    try:
        fps=max(1.,min(60.,float(capture.get(cv2.CAP_PROP_FPS) or 10.)))
        count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        stride=max(1,int(math.ceil(fps/4.)),int(math.ceil(count/60.)) if count else 1)
        duration=max(80,min(1200,int(round(1000.*stride/fps))))
        frames=[];index=0
        while len(frames)<60:
            ok,frame=capture.read()
            if not ok:break
            if index%stride==0:
                h,w=frame.shape[:2];scale=min(1.,480./max(h,w))
                nw=max(2,int(round(w*scale)));nh=max(2,int(round(h*scale)))
                if (nw,nh)!=(w,h):frame=cv2.resize(frame,(nw,nh),interpolation=cv2.INTER_AREA)
                rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb).quantize(colors=96,method=Image.Quantize.FASTOCTREE))
            index+=1
        if len(frames)<2:raise RuntimeError('Frame animasi tidak mencukupi.')
        os.makedirs(os.path.dirname(dest),exist_ok=True)
        frames[0].save(tmp,format='GIF',save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=False,disposal=2)
        if os.path.getsize(tmp)<1024:raise RuntimeError('Animasi kosong.')
        os.replace(tmp,dest)
        if archive:
            try:
                folder=os.path.join(archive,'Live_Photos');os.makedirs(folder,exist_ok=True)
                shutil.copy2(dest,os.path.join(folder,'Live_Photo_Frame_Animasi.gif'))
            except OSError as e:print('[LIVE_GIF_ARCHIVE_WARNING]',repr(e),flush=True)
        return 0
    finally:
        capture.release()
        if os.path.isfile(tmp):os.remove(tmp)
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('LIVE_GIF_ERROR='+repr(exc),flush=True);sys.exit(1)
