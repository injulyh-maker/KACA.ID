package id.kaca.tablet;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.*;
import android.net.Uri;
import android.provider.MediaStore;
import android.view.*;
import android.widget.*;
import android.text.InputType;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import android.util.Base64;
import org.json.*;

/** Offline-first basic Android booth. Does not imitate DSLR/live-photo/printing parity. */
public final class MainActivity extends Activity {
 static final String CLOUD="https://kacastudio.id";
 static final int PICK_FRAME=101, TAKE_PHOTO=102;
 final ExecutorService worker=Executors.newSingleThreadExecutor();
 android.content.SharedPreferences prefs;
 TextView state; ImageView preview; EditText email, password, code, name;
 Uri pendingCameraUri,frameUri; Bitmap lastResult;
 final ArrayList<JSONObject> queue=new ArrayList<>();

 @Override public void onCreate(Bundle b){super.onCreate(b);
  prefs=getSharedPreferences("kaca_tablet",MODE_PRIVATE);
  if(prefs.getString("device_id","").isEmpty())prefs.edit().putString("device_id",UUID.randomUUID().toString()).apply();
  try{JSONArray a=new JSONArray(prefs.getString("pending","[]"));for(int i=0;i<a.length();i++)queue.add(a.getJSONObject(i));}catch(Exception ignored){}
  try{String saved=prefs.getString("frame_uri","");if(!saved.isEmpty())frameUri=Uri.parse(saved);}catch(Exception ignored){}
  draw();updateStatus();
 }
 TextView text(String msg,int size){TextView v=new TextView(this);v.setText(msg);v.setTextColor(Color.WHITE);v.setTextSize(size);v.setPadding(0,9,0,9);return v;}
 EditText entry(String hint,boolean secret){EditText e=new EditText(this);e.setSingleLine(true);e.setHint(hint);e.setTextColor(Color.WHITE);e.setHintTextColor(Color.LTGRAY);if(secret)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);return e;}
 Button btn(String label,Runnable cb){Button b=new Button(this);b.setText(label);b.setOnClickListener(v->cb.run());return b;}
 void message(String m){runOnUiThread(()->new AlertDialog.Builder(this).setMessage(m).setPositiveButton("OK",null).show());}
 void draw(){ScrollView sc=new ScrollView(this);LinearLayout col=new LinearLayout(this);col.setPadding(24,24,24,24);col.setOrientation(LinearLayout.VERTICAL);col.setBackgroundColor(Color.rgb(11,25,49));sc.addView(col);
  col.addView(text("KACA.ID • TABLET",25));col.addView(text("Studio foto Android • Frame sendiri • Lisensi digital offline",14));
  state=text("Memeriksa lisensi…",15);col.addView(state);
  col.addView(btn("1. Aktivasi Akun & Lisensi",this::activationDialog));
  col.addView(btn("2. Upload Frame PNG",()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("image/png");i.addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,PICK_FRAME);}));
  col.addView(btn("3. Mulai Sesi Foto",this::capture));
  col.addView(btn("Sinkronkan Sesi ke Cloud",this::sync));
  col.addView(btn("Lihat Paket & Harga",()->{Intent browser=new Intent(Intent.ACTION_VIEW,Uri.parse(CLOUD+"/paket"));startActivity(browser);}));
  col.addView(text("Foto disimpan ke Pictures/KACA-ID. Pilihan frame lokal hanya berlaku di tablet ini. Mode offline tetap aktif sampai lisensi berakhir.",13));
  preview=new ImageView(this);preview.setAdjustViewBounds(true);preview.setMinimumHeight(200);preview.setBackgroundColor(Color.rgb(32,54,89));col.addView(preview);setContentView(sc);
 }
 void updateStatus(){String result;
  try{JSONObject v=verifiedLicense();long exp=v.getLong("exp");result="LISENSI AKTIF sampai "+new SimpleDateFormat("dd MMM yyyy HH:mm",Locale.forLanguageTag("id-ID")).format(new Date(exp*1000));}
  catch(Exception ex){result="SESI FOTO TERKUNCI • "+ex.getMessage();}
  result+="\nAntrean sesi menunggu Cloud: "+queue.size();String r=result;runOnUiThread(()->state.setText(r));
 }
 String sha256(String value)throws Exception{byte[] d=MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));StringBuilder h=new StringBuilder();for(byte b:d)h.append(String.format(Locale.ROOT,"%02x",b&255));return h.toString();}
 byte[] un64(String s){return Base64.decode(s,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);}
 JSONObject verifiedLicense()throws Exception{
   String offline=prefs.getString("license","");String pem=prefs.getString("public_key","");if(offline.isEmpty()||pem.isEmpty())throw new Exception("Aktivasi diperlukan");
   String[] parts=offline.split("\\.");if(parts.length!=2)throw new Exception("Format lisensi salah");
   byte[] keyBytes=Base64.decode(pem.replace("-----BEGIN PUBLIC KEY-----","").replace("-----END PUBLIC KEY-----","").replaceAll("\\s",""),Base64.DEFAULT);
   PublicKey pub=KeyFactory.getInstance("Ed25519").generatePublic(new X509EncodedKeySpec(keyBytes));
   Signature verifier=Signature.getInstance("Ed25519");verifier.initVerify(pub);verifier.update(parts[0].getBytes(StandardCharsets.UTF_8));
   if(!verifier.verify(un64(parts[1])))throw new Exception("Tanda tangan lisensi tidak sah");
   JSONObject payload=new JSONObject(new String(un64(parts[0]),StandardCharsets.UTF_8));
   if(!sha256(prefs.getString("device_id","")).equals(payload.optString("device_hash")))throw new Exception("Lisensi bukan untuk perangkat ini");
   long now=System.currentTimeMillis()/1000,max=prefs.getLong("max_clock",0);
   if(now+300<max)throw new Exception("Jam tablet mundur. Perbaiki tanggal/jam.");
   if(now>payload.getLong("exp"))throw new Exception("Lisensi kedaluwarsa");
   if(now>max+300)prefs.edit().putLong("max_clock",now).apply();
   return payload;
 }
 void activationDialog(){LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(20,0,20,0);
  email=entry("Email akun KACA.ID",false);password=entry("Password akun",true);code=entry("Kode lisensi",false);name=entry("Nama booth/tablet",false);
  name.setText(prefs.getString("booth_name","") );
  for(EditText e:new EditText[]{email,password,code,name})layout.addView(e);
  new AlertDialog.Builder(this).setTitle("Aktivasi lisensi tablet").setView(layout).setNegativeButton("Batal",null).setPositiveButton("Aktifkan",(d,w)->activate(email.getText().toString().trim(),password.getText().toString(),code.getText().toString().trim(),name.getText().toString().trim())).show();
 }
 JSONObject request(String route,JSONObject data,String bearer,String boothId,String boothKey)throws Exception{
   URL url=new URL(CLOUD+route);HttpsURLConnectionFix.verifyHttps(url);
   HttpURLConnection c=(HttpURLConnection)url.openConnection();c.setConnectTimeout(12000);c.setReadTimeout(12000);c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");
   if(bearer!=null)c.setRequestProperty("Authorization","Bearer "+bearer);
   if(boothId!=null){c.setRequestProperty("X-Booth-Id",boothId);c.setRequestProperty("X-Booth-Key",boothKey);}
   try(OutputStream os=c.getOutputStream()){os.write(data.toString().getBytes(StandardCharsets.UTF_8));}
   int status=c.getResponseCode();InputStream stream=status>=200&&status<300?c.getInputStream():c.getErrorStream();ByteArrayOutputStream buf=new ByteArrayOutputStream();if(stream!=null)try(stream){byte[] bytes=new byte[4096];int n;while((n=stream.read(bytes))!=-1)buf.write(bytes,0,n);}
   JSONObject response=new JSONObject(buf.toString("UTF-8"));c.disconnect();if(status<200||status>=300)throw new Exception(response.optString("detail","HTTP "+status));return response;
 }
 static final class HttpsURLConnectionFix{static void verifyHttps(URL u)throws Exception{if(!"https".equals(u.getProtocol()))throw new Exception("Hanya HTTPS diizinkan");}}
 void activate(String em,String pw,String license,String booth){if(em.isEmpty()||pw.isEmpty()||license.isEmpty()||booth.isEmpty()){message("Lengkapi semua kolom.");return;}
  worker.execute(()->{try{JSONObject login=request("/api/auth/login",new JSONObject().put("email",em).put("password",pw),null,null,null);
   JSONObject activation=request("/api/booths/activate",new JSONObject().put("license_code",license).put("device_id",prefs.getString("device_id","")).put("name",booth),login.getString("token"),null,null);
   // Verify the cryptographic signature *before* committing credentials.
   String oldLic=prefs.getString("license","");String oldKey=prefs.getString("public_key","");
   if(!oldKey.isEmpty()&&!oldKey.equals(activation.getString("license_public_key")))throw new Exception("Kunci Cloud berbeda dari aktivasi sebelumnya. Hubungi admin.");
   prefs.edit().putString("license",activation.getString("offline_license")).putString("public_key",activation.getString("license_public_key")).apply();
   try{verifiedLicense();}catch(Exception e){prefs.edit().putString("license",oldLic).putString("public_key",oldKey).apply();throw e;}
   prefs.edit().putString("booth_id",activation.getString("booth_id")).putString("booth_key",activation.getString("booth_key")).putString("booth_name",booth).apply();
   runOnUiThread(()->{updateStatus();message("Lisensi aktif. Foto bisa diambil offline.");});
  }catch(Exception ex){message("Aktivasi gagal: "+ex.getMessage());}});
 }
 void capture(){try{verifiedLicense();}catch(Exception e){message("Sesi terkunci: "+e.getMessage());updateStatus();return;}
  try{
   android.content.ContentValues values=new android.content.ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"KACA-RAW-"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/KACA-ID/Originals");
   pendingCameraUri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);
   if(pendingCameraUri==null)throw new IOException("Tidak dapat menyiapkan file kamera");
   Intent take=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);take.putExtra(MediaStore.EXTRA_OUTPUT,pendingCameraUri);take.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(take,TAKE_PHOTO);
  }catch(Exception ex){message("Kamera gagal dibuka: "+ex.getMessage());}
 }
 @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);
  if(requestCode==PICK_FRAME&&resultCode==RESULT_OK&&data!=null){frameUri=data.getData();try{getContentResolver().takePersistableUriPermission(frameUri,Intent.FLAG_GRANT_READ_URI_PERMISSION);prefs.edit().putString("frame_uri",frameUri.toString()).apply();message("Frame PNG disimpan sebagai pilihan sesi berikutnya.");}catch(Exception e){message("Frame tidak dapat dibaca: "+e.getMessage());}return;}
  if(requestCode==TAKE_PHOTO&&resultCode==RESULT_OK&&pendingCameraUri!=null){final Uri source=pendingCameraUri;worker.execute(()->combine(source));}
 }
 void combine(Uri source){try{
   // Decode a bounded bitmap to avoid OOM on 50MP cameras.
   BitmapFactory.Options o=new BitmapFactory.Options();o.inJustDecodeBounds=true;
   try(InputStream is=getContentResolver().openInputStream(source)){BitmapFactory.decodeStream(is,null,o);}
   int sample=1;while(o.outWidth/sample>2400||o.outHeight/sample>2400)sample*=2;
   o.inJustDecodeBounds=false;o.inSampleSize=sample;
   Bitmap photo;try(InputStream is=getContentResolver().openInputStream(source)){photo=BitmapFactory.decodeStream(is,null,o);}
   if(photo==null)throw new IOException("Foto kosong");
   // Result orientation follows the captured JPEG metadata; do not stretch aspect ratio.
   int width=photo.getWidth(),height=photo.getHeight();Bitmap result=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(result);
   canvas.drawBitmap(photo,0,0,null);
   if(frameUri!=null){try(InputStream f=getContentResolver().openInputStream(frameUri)){Bitmap frame=BitmapFactory.decodeStream(f);if(frame!=null){canvas.drawBitmap(frame,null,new Rect(0,0,width,height),new Paint(Paint.FILTER_BITMAP_FLAG));frame.recycle();}}}
   android.content.ContentValues values=new android.content.ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"KACA-RESULT-"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/KACA-ID/Results");
   Uri dest=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);if(dest==null)throw new IOException("Tidak dapat menyimpan hasil");
   try(OutputStream out=getContentResolver().openOutputStream(dest)){if(out==null||!result.compress(Bitmap.CompressFormat.JPEG,95,out))throw new IOException("JPEG gagal disimpan");}
   lastResult=result;JSONObject item=new JSONObject().put("id",UUID.randomUUID().toString()).put("finished_at",new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss",Locale.ROOT).format(new Date())).put("event_name","").put("mode","PHOTO").put("payment_method","").put("amount_idr",0).put("verified_paid",false).put("photo_count",1);
   queue.add(item);persistQueue();runOnUiThread(()->{preview.setImageBitmap(lastResult);updateStatus();message("Foto dan frame tersimpan di galeri. Sesi dapat disinkronkan nanti.");});
  }catch(Exception e){message("Gagal memproses foto: "+e.getMessage());}
 }
 void persistQueue(){JSONArray a=new JSONArray();for(JSONObject q:queue)a.put(q);prefs.edit().putString("pending",a.toString()).apply();}
 void sync(){try{verifiedLicense();}catch(Exception e){message(e.getMessage());return;}
  worker.execute(()->{try{JSONObject request=new JSONObject().put("version","0.9.90-tablet").put("remote_until",0).put("sessions",new JSONArray(queue));
   JSONObject response=request("/api/agent/sync",request,null,prefs.getString("booth_id",""),prefs.getString("booth_key",""));if(!response.optBoolean("ok"))throw new Exception("Cloud tidak mengonfirmasi sync");
   int synced=response.optInt("accepted_sessions",0);queue.clear();persistQueue();runOnUiThread(()->{updateStatus();message("Sinkronisasi berhasil: "+synced+" sesi.");});
  }catch(Exception e){message("Sinkronisasi akan dicoba lagi: "+e.getMessage());}});
 }
 @Override public void onDestroy(){worker.shutdown();super.onDestroy();}
}
