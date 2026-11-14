package id.kaca.tablet;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintDocumentInfo;
import android.print.PrintManager;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.List;

/**
 * Android's print spooler discovers printers through installed Print Services.
 * Custom 4R and 2R media sizes are hints; the printer/driver must support them.
 * Never claim a print job completed until the system print service confirms it.
 */
final class AndroidPhotoPrinter {
    private AndroidPhotoPrinter(){}

    static JSONObject services(Activity activity){
        JSONObject result=new JSONObject();
        try {
            PrintManager pm=(PrintManager)activity.getSystemService(Context.PRINT_SERVICE);
            result.put("available",pm!=null);
            JSONArray names=new JSONArray();
            Intent intent=new Intent("android.printservice.PrintService");
            List<ResolveInfo> services=activity.getPackageManager().queryIntentServices(intent,0);
            for(ResolveInfo service:services){
                CharSequence label=service.loadLabel(activity.getPackageManager());
                names.put(label==null?service.serviceInfo.packageName:label.toString());
            }
            result.put("services",names);
            result.put("note","Printer fisik dipilih/ditemukan melalui dialog Cetak Android; daftar ini hanya layanan cetak terpasang, bukan konfirmasi koneksi printer.");
        }catch(Exception e){try{result.put("available",false);result.put("error",e.getMessage());}catch(Exception ignored){}}
        return result;
    }

    private static final class Paper {
        final String id,name;
        final int widthMils,heightMils;
        Paper(String id,String name,int w,int h){this.id=id;this.name=name;this.widthMils=w;this.heightMils=h;}
    }
    static Paper paper(String selected){
        switch(selected){
            case "2R": return new Paper("KACA_2R","2R 2.5 x 3.5 inci",2500,3500);
            case "2R_STRIP": return new Paper("KACA_2R_STRIP","2R strip 2 x 6 inci",2000,6000);
            default: return new Paper("KACA_4R","4R 4 x 6 inci",4000,6000);
        }
    }
    static void print(Activity activity,Uri image,String selected,String fitting,boolean photoLandscape){
        if(image==null)throw new IllegalStateException("Belum ada foto hasil untuk dicetak.");
        PrintManager manager=(PrintManager)activity.getSystemService(Context.PRINT_SERVICE);
        if(manager==null)throw new IllegalStateException("Layanan Cetak Android tidak tersedia.");
        Paper chosen=paper(selected);
        boolean landscape=photoLandscape && !"2R_STRIP".equals(selected);
        PrintAttributes.MediaSize size=new PrintAttributes.MediaSize(chosen.id,chosen.name,chosen.widthMils,chosen.heightMils);
        if(landscape)size=size.asLandscape();
        final int pointsW=Math.round(size.getWidthMils()*72f/1000f),pointsH=Math.round(size.getHeightMils()*72f/1000f);
        final boolean crop="fill".equals(fitting);
        final PrintAttributes options=new PrintAttributes.Builder()
                .setMediaSize(size)
                .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
                .setResolution(new PrintAttributes.Resolution("kaca300","300 DPI",300,300))
                .setMinMargins(PrintAttributes.Margins.NO_MARGINS)
                .build();
        PrintDocumentAdapter adapter=new PrintDocumentAdapter(){
            @Override public void onLayout(PrintAttributes oldAttributes,PrintAttributes newAttributes,
                                           CancellationSignal cancel,LayoutResultCallback callback,Bundle extras){
                if(cancel.isCanceled()){callback.onLayoutCancelled();return;}
                PrintDocumentInfo info=new PrintDocumentInfo.Builder("KACA-ID-"+chosen.id+".pdf")
                        .setContentType(PrintDocumentInfo.CONTENT_TYPE_PHOTO).setPageCount(1).build();
                callback.onLayoutFinished(info,true);
            }
            @Override public void onWrite(android.print.PageRange[] pages,ParcelFileDescriptor destination,
                                          CancellationSignal cancel,WriteResultCallback callback){
                new Thread(()->{
                    PdfDocument doc=new PdfDocument();
                    try{
                        if(cancel.isCanceled()){callback.onWriteCancelled();return;}
                        BitmapFactory.Options bounds=new BitmapFactory.Options();
                        bounds.inJustDecodeBounds=true;
                        try(InputStream in=activity.getContentResolver().openInputStream(image)){
                            if(in==null)throw new IllegalStateException("Tidak dapat membaca foto.");
                            BitmapFactory.decodeStream(in,null,bounds);
                        }
                        if(bounds.outWidth<1||bounds.outHeight<1)throw new IllegalStateException("Foto kosong.");
                        int sampling=1;
                        while(bounds.outWidth/sampling>3600||bounds.outHeight/sampling>3600)sampling*=2;
                        BitmapFactory.Options decode=new BitmapFactory.Options();decode.inSampleSize=sampling;decode.inPreferredConfig=Bitmap.Config.ARGB_8888;
                        Bitmap photo;
                        try(InputStream in=activity.getContentResolver().openInputStream(image)){
                            photo=BitmapFactory.decodeStream(in,null,decode);
                        }
                        if(photo==null)throw new IllegalStateException("Tidak dapat mendekode foto.");
                        try{
                            PdfDocument.PageInfo pageInfo=new PdfDocument.PageInfo.Builder(pointsW,pointsH,1).create();
                            PdfDocument.Page page=doc.startPage(pageInfo);
                            Canvas canvas=page.getCanvas();
                            canvas.drawColor(Color.WHITE);
                            float scale=crop?Math.max(pointsW/(float)photo.getWidth(),pointsH/(float)photo.getHeight()):
                                               Math.min(pointsW/(float)photo.getWidth(),pointsH/(float)photo.getHeight());
                            float dw=photo.getWidth()*scale,dh=photo.getHeight()*scale;
                            float left=(pointsW-dw)/2f,top=(pointsH-dh)/2f;
                            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
                            if(crop){
                                canvas.save();canvas.clipRect(0,0,pointsW,pointsH);
                                canvas.drawBitmap(photo,null,new RectF(left,top,left+dw,top+dh),paint);
                                canvas.restore();
                            }else canvas.drawBitmap(photo,null,new RectF(left,top,left+dw,top+dh),paint);
                            doc.finishPage(page);
                        }finally{photo.recycle();}
                        if(cancel.isCanceled()){callback.onWriteCancelled();return;}
                        try(FileOutputStream out=new FileOutputStream(destination.getFileDescriptor())){doc.writeTo(out);}
                        callback.onWriteFinished(new android.print.PageRange[]{android.print.PageRange.ALL_PAGES});
                    }catch(Exception error){callback.onWriteFailed("Gagal membuat halaman cetak: "+error.getMessage());}
                    finally{doc.close();}
                },"KACA-Print-PDF").start();
            }
        };
        manager.print("KACA.ID - "+chosen.name,adapter,options);
    }
}
