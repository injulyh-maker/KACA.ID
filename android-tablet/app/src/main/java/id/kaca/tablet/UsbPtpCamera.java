package id.kaca.tablet;

import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

/**
 * First implementation of ISO 15740 / USB Still Image Class PTP operations.
 * This is an optional interoperability path, NOT Canon EDSDK or Nikon SDK.
 * A camera must expose the PTP still-image interface and support
 * InitiateCapture, GetObjectHandles, GetObjectInfo, and GetObject.
 * No camera-specific vendor commands, property writes or firmware actions.
 */
final class UsbPtpCamera implements AutoCloseable {
    private static final int USB_PTP_CLASS=UsbConstants.USB_CLASS_STILL_IMAGE;
    private static final int TYPE_COMMAND=1, TYPE_DATA=2, TYPE_RESPONSE=3, TYPE_EVENT=4;
    private static final int OK=0x2001, MAX_PAYLOAD=40*1024*1024;
    private static final int GET_DEVICE_INFO=0x1001, OPEN_SESSION=0x1002, CLOSE_SESSION=0x1003;
    private static final int GET_OBJECT_HANDLES=0x1007, GET_OBJECT_INFO=0x1008;
    private static final int GET_OBJECT=0x1009, INITIATE_CAPTURE=0x100E;
    private final UsbDeviceConnection connection;
    private final UsbInterface ptp;
    private final UsbEndpoint input,output;
    private final byte[] buffer=new byte[16384];
    private int at=0,limit=0,transaction=1;
    private boolean session=false;

    static boolean supports(UsbDevice device){
        return locate(device)!=null;
    }
    private static UsbInterface locate(UsbDevice device){
        for(int i=0;i<device.getInterfaceCount();i++){
            UsbInterface face=device.getInterface(i);
            if(face.getInterfaceClass()!=USB_PTP_CLASS)continue;
            UsbEndpoint in=null,out=null;
            for(int n=0;n<face.getEndpointCount();n++){
                UsbEndpoint endpoint=face.getEndpoint(n);
                if(endpoint.getType()!=UsbConstants.USB_ENDPOINT_XFER_BULK)continue;
                if(endpoint.getDirection()==UsbConstants.USB_DIR_IN)in=endpoint;
                if(endpoint.getDirection()==UsbConstants.USB_DIR_OUT)out=endpoint;
            }
            if(in!=null&&out!=null)return face;
        }
        return null;
    }
    UsbPtpCamera(UsbManager manager,UsbDevice device) throws IOException{
        if(!manager.hasPermission(device))throw new IOException("Izinkan akses kamera USB terlebih dahulu.");
        ptp=locate(device);
        if(ptp==null)throw new IOException("Kamera tidak menyediakan antarmuka PTP USB dengan endpoint bulk IN/OUT.");
        UsbDeviceConnection open=manager.openDevice(device);
        if(open==null)throw new IOException("Tidak dapat membuka koneksi kamera USB.");
        connection=open;
        if(!connection.claimInterface(ptp,true)){connection.close();throw new IOException("Antarmuka USB PTP sedang digunakan aplikasi lain.");}
        UsbEndpoint in=null,out=null;
        for(int n=0;n<ptp.getEndpointCount();n++){
            UsbEndpoint ep=ptp.getEndpoint(n);
            if(ep.getType()!=UsbConstants.USB_ENDPOINT_XFER_BULK)continue;
            if(ep.getDirection()==UsbConstants.USB_DIR_IN)in=ep;
            if(ep.getDirection()==UsbConstants.USB_DIR_OUT)out=ep;
        }
        input=in;output=out;
    }

    private static int u16(byte[] b,int p){return (b[p]&255)|((b[p+1]&255)<<8);}
    private static long u32(byte[] b,int p){
        return ((long)b[p]&255)|(((long)b[p+1]&255)<<8)|(((long)b[p+2]&255)<<16)|(((long)b[p+3]&255)<<24);
    }
    private static void put16(byte[] b,int p,int n){b[p]=(byte)n;b[p+1]=(byte)(n>>>8);}
    private static void put32(byte[] b,int p,long n){for(int i=0;i<4;i++)b[p+i]=(byte)(n>>>(8*i));}
    private void send(int operation,int tx,long...params)throws IOException{
        if(params.length>5)throw new IOException("Terlalu banyak parameter PTP.");
        byte[] cmd=new byte[12+4*params.length];
        put32(cmd,0,cmd.length);put16(cmd,4,TYPE_COMMAND);put16(cmd,6,operation);put32(cmd,8,tx);
        for(int i=0;i<params.length;i++)put32(cmd,12+i*4,params[i]);
        int sent=0;
        while(sent<cmd.length){
            // Device-bound PTP commands are tiny; do not silently accept partial sends.
            byte[] part;
            if(sent==0)part=cmd;else{part=new byte[cmd.length-sent];System.arraycopy(cmd,sent,part,0,part.length);}
            int wrote=connection.bulkTransfer(output,part,part.length,3000);
            if(wrote<=0)throw new IOException("USB PTP gagal mengirim operasi 0x"+Integer.toHexString(operation));
            sent+=wrote;
        }
    }
    private void receiveFully(byte[] dst,int offset,int length)throws IOException{
        int done=0;
        while(done<length){
            if(at==limit){
                int count=connection.bulkTransfer(input,buffer,buffer.length,4000);
                if(count<=0)throw new IOException("Kamera tidak merespons USB PTP (timeout/koneksi terputus).");
                at=0;limit=count;
            }
            int n=Math.min(limit-at,length-done);
            System.arraycopy(buffer,at,dst,offset+done,n);at+=n;done+=n;
        }
    }
    private static final class Container{
        int type,code;long tx;byte[] payload;
    }
    private Container receive()throws IOException{
        byte[] header=new byte[12];receiveFully(header,0,header.length);
        long full=u32(header,0);
        if(full<12||full>MAX_PAYLOAD+12L)throw new IOException("Ukuran data USB PTP tidak aman: "+full);
        Container c=new Container();c.type=u16(header,4);c.code=u16(header,6);c.tx=u32(header,8);
        c.payload=new byte[(int)full-12];
        receiveFully(c.payload,0,c.payload.length);
        return c;
    }
    private byte[] command(int operation,boolean expectData,long...params)throws IOException{
        int tx=operation==OPEN_SESSION?0:transaction++;
        send(operation,tx,params);
        byte[] data=null;
        for(int i=0;i<4;i++){
            Container p=receive();
            if(p.type==TYPE_EVENT)continue;
            if(p.tx!=tx)throw new IOException("Transaksi PTP tidak cocok: "+p.tx+" / "+tx);
            if(p.type==TYPE_DATA){
                if(!expectData||data!=null||p.code!=operation)throw new IOException("Respons data PTP tidak sesuai operasi.");
                data=p.payload;continue;
            }
            if(p.type!=TYPE_RESPONSE)throw new IOException("Jenis paket PTP tidak dikenali: "+p.type);
            if(p.code!=OK)throw new IOException("Perangkat menolak perintah PTP 0x"+Integer.toHexString(operation)+
                   " (kode 0x"+Integer.toHexString(p.code)+"). Periksa mode USB kamera dan kompatibilitas firmware.");
            if(expectData&&data==null)throw new IOException("Kamera mengembalikan data kosong untuk 0x"+Integer.toHexString(operation));
            return data==null?new byte[0]:data;
        }
        throw new IOException("Respons akhir PTP tidak diterima.");
    }
    private static final class Description{
        boolean capture;
        String model="Kamera PTP";
    }
    private static void need(byte[] d,int start,int length)throws IOException{
        if(start<0||length<0||start>d.length-length)throw new IOException("Data informasi PTP rusak/tidak lengkap.");
    }
    private static int skipString(byte[] d,int offset)throws IOException{
        need(d,offset,1);int chars=d[offset]&255;
        int bytes=1+2*chars;need(d,offset,bytes);return offset+bytes;
    }
    private static Description decodeDeviceInfo(byte[] d)throws IOException{
        // DeviceInfo: version(2), extension-id(4), extension-version(2),
        // extension description (PTP UTF-16 string), functional mode(2),
        // then operation codes (uint32 count + uint16 entries).
        int p=8;p=skipString(d,p);need(d,p,6);p+=2;
        long count=u32(d,p);p+=4;
        if(count>4096)throw new IOException("Daftar operasi kamera tidak valid.");
        need(d,p,(int)count*2);
        Description info=new Description();
        for(int i=0;i<count;i++)if(u16(d,p+i*2)==INITIATE_CAPTURE)info.capture=true;
        return info;
    }
    JSONObject probe()throws IOException{
        byte[] info=command(GET_DEVICE_INFO,true);
        Description d=decodeDeviceInfo(info);
        JSONObject value=new JSONObject();
        try{
            value.put("protocol","USB PTP");
            value.put("initiateCapture",d.capture);
            value.put("supported",d.capture);
            value.put("message",d.capture?"Perintah PTP InitiateCapture diumumkan kamera. Masih perlu uji pemotretan.":"Kamera terhubung PTP tetapi tidak mengumumkan InitiateCapture. Gunakan kamera bawaan atau SDK model khusus.");
        }catch(Exception ignored){}
        return value;
    }
    private void startSession()throws IOException{
        command(OPEN_SESSION,false,1);session=true;
    }
    private Set<Long> getHandles()throws IOException{
        byte[] data=command(GET_OBJECT_HANDLES,true,0xffffffffL,0,0);
        need(data,0,4);long count=u32(data,0);
        if(count>20000)throw new IOException("Terlalu banyak objek kamera untuk dipindai.");
        need(data,4,(int)count*4);
        Set<Long> handles=new HashSet<>();
        for(int n=0;n<count;n++)handles.add(u32(data,4+4*n));
        return handles;
    }
    private boolean jpegObject(long handle)throws IOException{
        byte[] info=command(GET_OBJECT_INFO,true,handle);
        need(info,0,12);
        int format=u16(info,4);
        long bytes=u32(info,8);
        return format==0x3801 && bytes>0 && bytes<MAX_PAYLOAD;
    }
    /**
     * Issue a standard shutter and download the first NEW JPEG handle.
     * Leaves the original JPEG on camera storage; never deletes camera objects.
     */
    byte[] captureJpeg()throws IOException,InterruptedException{
        Description d=decodeDeviceInfo(command(GET_DEVICE_INFO,true));
        if(!d.capture)throw new IOException("Kamera tidak mengumumkan dukungan PTP InitiateCapture. Driver khusus model diperlukan.");
        startSession();
        Set<Long> before=getHandles();
        command(INITIATE_CAPTURE,false,0,0);
        long deadline=System.currentTimeMillis()+24000;
        while(System.currentTimeMillis()<deadline){
            if(Thread.currentThread().isInterrupted())throw new InterruptedException("Pemotretan USB dibatalkan.");
            Thread.sleep(800);
            Set<Long> after=getHandles();
            for(Long handle:after){
                if(before.contains(handle))continue;
                if(!jpegObject(handle))continue;
                byte[] image=command(GET_OBJECT,true,handle);
                if(image.length<100||image[0]!=(byte)0xff||image[1]!=(byte)0xd8)
                    throw new IOException("Objek kamera bukan JPEG. Atur kamera RAW+JPEG/JPEG.");
                return image;
            }
        }
        throw new IOException("Kamera tidak menghasilkan JPEG baru selama 24 detik. Periksa storage, mode USB PTP, dan setelan JPEG.");
    }
    @Override public void close(){
        if(session){try{command(CLOSE_SESSION,false);}catch(Exception ignored){}session=false;}
        try{connection.releaseInterface(ptp);}catch(Exception ignored){}
        connection.close();
    }
}
