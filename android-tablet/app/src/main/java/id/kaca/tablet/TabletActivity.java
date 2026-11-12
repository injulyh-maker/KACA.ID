package id.kaca.tablet;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.content.ContentValues;
import android.util.Base64;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.webkit.WebViewAssetLoader;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.util.Arrays;

/**
 * Runs the exact Windows sidebar, palette and responsive HTML/CSS shell.
 * Camera capture, signed offline license and sync reuse MainActivity's native Android code.
 * Does NOT claim DSLR, desktop print, Live Photo or full desktop backend support.
 */
public final class TabletActivity extends MainActivity {
    private static final String ASSET_ORIGIN="https://appassets.androidplatform.net";
    private static final int FILE_PICKER_REQUEST=230;
    private static final int VIDEO_CAPTURE_REQUEST=231;
    private static final int CAMERA_PERMISSION_REQUEST=232;
    private WebView web;
    private WebViewAssetLoader assetLoader;
    private ValueCallback<Uri[]> fileCallback;
    private PermissionRequest webCameraRequest;
    private Uri lastVideoUri;

    @Override void draw() {
        // MainActivity uses these for native session processing callbacks.
        state=new TextView(this);
        preview=new ImageView(this);
        assetLoader=new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();
        web=new WebView(this);
        WebSettings cfg=web.getSettings();
        cfg.setJavaScriptEnabled(true);
        cfg.setDomStorageEnabled(true);
        cfg.setAllowFileAccess(false);
        cfg.setAllowContentAccess(false);
        cfg.setAllowFileAccessFromFileURLs(false);
        cfg.setAllowUniversalAccessFromFileURLs(false);
        cfg.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.addJavascriptInterface(new Bridge(),"AndroidBooth");
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                return assetLoader.shouldInterceptRequest(req.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                String url=req.getUrl().toString();
                if(url.startsWith(ASSET_ORIGIN+"/assets/"))return false;
                safeOpen(url);
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> callback,FileChooserParams params){
                if(fileCallback!=null)fileCallback.onReceiveValue(null);
                fileCallback=callback;
                try{startActivityForResult(params.createIntent(), FILE_PICKER_REQUEST);}
                catch(Exception e){fileCallback.onReceiveValue(null);fileCallback=null;return false;}
                return true;
            }
            @Override public void onPermissionRequest(PermissionRequest req){
                runOnUiThread(()->{
                    Uri origin=req.getOrigin();
                    if(origin==null || !"https".equals(origin.getScheme()) || !"appassets.androidplatform.net".equals(origin.getHost()) || !Arrays.asList(req.getResources()).contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) {
                        req.deny();return;
                    }
                    webCameraRequest=req;
                    if(checkSelfPermission(Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED){
                        req.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});webCameraRequest=null;
                    } else requestPermissions(new String[]{Manifest.permission.CAMERA},CAMERA_PERMISSION_REQUEST);
                });
            }
        });
        setContentView(web);
        web.loadUrl(ASSET_ORIGIN+"/assets/www/index.html");
    }

    private void safeOpen(String raw){
        try{
            Uri uri=Uri.parse(raw);
            String host=uri.getHost();
            if(!"https".equalsIgnoreCase(uri.getScheme()))return;
            if(!"kacastudio.id".equalsIgnoreCase(host) && !"wa.me".equalsIgnoreCase(host))return;
            startActivity(new Intent(Intent.ACTION_VIEW,uri));
        }catch(Exception ignored){}
    }
    private void js(String expr){runOnUiThread(()->{if(web!=null)web.evaluateJavascript(expr,null);});}
    private void notice(String message){js("window.kacaAndroid?.notice("+JSONObject.quote(message)+")");}
    @Override void message(String m){notice(m);}
    @Override void updateStatus(){super.updateStatus();js("window.kacaAndroid?.statusChanged()");}

    @Override void combine(Uri source){
        Bitmap previous=lastResult;
        super.combine(source);
        if(lastResult==null||lastResult==previous)return;
        Bitmap bitmap=lastResult;
        int width=bitmap.getWidth();
        if(width<=0)return;
        int maxWidth=960;
        Bitmap scaled=width>maxWidth?Bitmap.createScaledBitmap(bitmap,maxWidth,Math.max(1,(int)((double)bitmap.getHeight()*maxWidth/width)),true):bitmap;
        ByteArrayOutputStream stream=new ByteArrayOutputStream();
        if(scaled.compress(Bitmap.CompressFormat.JPEG,75,stream)){
            String encoded=Base64.encodeToString(stream.toByteArray(),Base64.NO_WRAP);
            js("window.kacaAndroid?.onPhotoReady("+JSONObject.quote(encoded)+")");
        }
        if(scaled!=bitmap)scaled.recycle();
    }

    private void recordVideo(){
        try{
            verifiedLicense();
            ContentValues values=new ContentValues();
            values.put(MediaStore.Video.Media.DISPLAY_NAME,"KACA-VIDEO-"+System.currentTimeMillis()+".mp4");
            values.put(MediaStore.Video.Media.MIME_TYPE,"video/mp4");
            values.put(MediaStore.Video.Media.RELATIVE_PATH,"Movies/KACA-ID");
            lastVideoUri=getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI,values);
            Intent intent=new Intent(MediaStore.ACTION_VIDEO_CAPTURE);
            intent.putExtra(MediaStore.EXTRA_OUTPUT,lastVideoUri);
            intent.putExtra(MediaStore.EXTRA_DURATION_LIMIT,prefs.getInt("video_duration_seconds",30));
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(intent,VIDEO_CAPTURE_REQUEST);
        }catch(Exception e){notice("Video tidak dapat dimulai: "+e.getMessage());}
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        if(requestCode==FILE_PICKER_REQUEST){
            if(fileCallback!=null){fileCallback.onReceiveValue(resultCode==Activity.RESULT_OK?WebChromeClient.FileChooserParams.parseResult(resultCode,data):null);fileCallback=null;}
            return;
        }
        if(requestCode==VIDEO_CAPTURE_REQUEST){
            if(resultCode==Activity.RESULT_OK)notice("Video tersimpan di Movies/KACA-ID.");
            else notice("Perekaman video dibatalkan.");
            return;
        }
        super.onActivityResult(requestCode,resultCode,data);
    }
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] grantResults){
        super.onRequestPermissionsResult(requestCode,permissions,grantResults);
        if(requestCode==CAMERA_PERMISSION_REQUEST&&webCameraRequest!=null){
            PermissionRequest pending=webCameraRequest;webCameraRequest=null;
            if(grantResults.length>0&&grantResults[0]==PackageManager.PERMISSION_GRANTED)pending.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
            else pending.deny();
        }
    }
    @Override public void onDestroy(){
        if(webCameraRequest!=null){webCameraRequest.deny();webCameraRequest=null;}
        if(fileCallback!=null){fileCallback.onReceiveValue(null);fileCallback=null;}
        if(web!=null){web.removeJavascriptInterface("AndroidBooth");web.destroy();web=null;}
        super.onDestroy();
    }

    /** Interface exposed ONLY to bundled appassets UI, never third party sites. */
    public final class Bridge {
        @JavascriptInterface public void configure(String raw){
            try{
                if(raw==null||raw.length()>300)throw new Exception("Input pengaturan tidak valid");
                JSONObject opts=new JSONObject(raw);
                int quality=opts.optInt("jpegQuality",95);
                int duration=opts.optInt("videoDuration",30);
                if(quality<65||quality>100||duration<5||duration>180)throw new Exception("Nilai pengaturan di luar batas");
                prefs.edit().putInt("jpeg_quality",quality).putInt("video_duration_seconds",duration).apply();
            }catch(Exception e){notice("Pengaturan Android gagal: "+e.getMessage());}
        }
        @JavascriptInterface public String status(){
            JSONObject obj=new JSONObject();
            try{
                JSONObject p=verifiedLicense();
                obj.put("active",true);obj.put("expiresAt",p.optLong("exp"));
                obj.put("message","Lisensi aktif sampai "+new java.text.SimpleDateFormat("dd MMM yyyy",java.util.Locale.forLanguageTag("id-ID")).format(new java.util.Date(p.getLong("exp")*1000)));
            }catch(Exception e){try{obj.put("active",false);obj.put("message",e.getMessage());}catch(Exception ignored){}}
            try{obj.put("boothName",prefs.getString("booth_name",""));obj.put("pending",queue.size());}catch(Exception ignored){}
            return obj.toString();
        }
        @JavascriptInterface public void activate(String email,String password,String code,String booth){
            if(email.length()>180||password.length()>256||code.length()>100||booth.length()>100){notice("Input terlalu panjang");return;}
            TabletActivity.this.activate(email,password,code,booth);
        }
        @JavascriptInterface public void capture(){runOnUiThread(()->TabletActivity.this.capture());}
        @JavascriptInterface public void recordVideo(){runOnUiThread(()->TabletActivity.this.recordVideo());}
        @JavascriptInterface public void sync(){runOnUiThread(()->TabletActivity.this.sync());}
        @JavascriptInterface public void setFrame(String dataUrl){
            worker.execute(()->{
                try{
                    if(dataUrl==null||!dataUrl.startsWith("data:image/png;base64,")||dataUrl.length()>8500000)throw new Exception("PNG harus di bawah 6 MB");
                    byte[] bytes=Base64.decode(dataUrl.substring("data:image/png;base64,".length()),Base64.DEFAULT);
                    if(bytes.length>6*1024*1024||bytes.length<8||bytes[0]!=(byte)0x89||bytes[1]!=0x50||bytes[2]!=0x4e||bytes[3]!=0x47)throw new Exception("File harus PNG yang valid");
                    File file=new File(getFilesDir(),"customer-frame.png");
                    try(FileOutputStream output=new FileOutputStream(file)){output.write(bytes);}
                    frameUri=Uri.fromFile(file);
                    prefs.edit().putString("frame_uri",frameUri.toString()).apply();
                    notice("Frame PNG disimpan dan siap digunakan.");
                }catch(Exception e){notice("Gagal menyimpan frame: "+e.getMessage());}
            });
        }
        @JavascriptInterface public void shareLastPhoto(){runOnUiThread(()->{
            if(lastResultUri==null){notice("Belum ada foto untuk dibagikan.");return;}
            Intent i=new Intent(Intent.ACTION_SEND);i.setType("image/jpeg");i.putExtra(Intent.EXTRA_STREAM,lastResultUri);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(i,"Bagikan hasil KACA.ID"));
        });}
        @JavascriptInterface public void openGallery(){runOnUiThread(()->{
            Intent i=new Intent(Intent.ACTION_VIEW);i.setType("image/*");
            try{startActivity(i);}catch(Exception e){notice("Galeri Android tidak tersedia.");}
        });}
        @JavascriptInterface public void openUrl(String url){runOnUiThread(()->safeOpen(url));}
        @JavascriptInterface public void toggleFullscreen(){runOnUiThread(()->{
            View decor=getWindow().getDecorView();int next=decor.getSystemUiVisibility() ^ View.SYSTEM_UI_FLAG_FULLSCREEN;decor.setSystemUiVisibility(next);
        });}
    }
}
