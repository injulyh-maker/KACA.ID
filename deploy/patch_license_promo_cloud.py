#!/usr/bin/env python3
"""Safely merge license renewal and pricing into KACA.ID's production Cloud.
Default: read-only validation. Run with --apply only after a successful dry run.
"""
import argparse
import ast
from datetime import datetime
from pathlib import Path
import re
import sys
from urllib.request import urlopen

ROOT = Path('/opt/kaca-id/KACA-ID-PUBLIC-VPS')
COMMIT = '7baa85dda4dd6fab9fd9ede2a365dd428cbab662'
RAW = 'https://raw.githubusercontent.com/injulyh-maker/KACA.ID/'+COMMIT+'/'

def fetch(name):
    with urlopen(RAW+name,timeout=25) as response:
        return response.read().decode('utf-8')

def ast_node(src,name):
    for node in ast.parse(src).body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.name==name:
            return node
    raise ValueError('Fungsi belum ditemukan: '+name)

def bounds(node):
    decorators=getattr(node,'decorator_list',[])
    return min([node.lineno]+[x.lineno for x in decorators]),node.end_lineno

def part(src,node):
    a,b=bounds(node)
    return ''.join(src.splitlines(keepends=True)[a-1:b])

def replace_node(src,ref,name):
    a,b=bounds(ast_node(src,name))
    lines=src.splitlines(keepends=True)
    lines[a-1:b]=[part(ref,ast_node(ref,name)).rstrip('\n')+'\n']
    result=''.join(lines)
    ast.parse(result)
    return result

def patch_server(src,ref):
    for name in ('public_plans','PlanPrice','admin_plans','set_plan_price'):
        src=replace_node(src,ref,name)
    if 'original_price_idr' not in part(src,ast_node(src,'init_db')):
        marker="            cols=[x['name'] for x in con.execute('PRAGMA table_info(booths)').fetchall()]"
        if marker not in src: raise ValueError('Titik migrasi harga tidak cocok dengan produksi.')
        migration='''            plan_columns=[c['name'] for c in con.execute('PRAGMA table_info(plans)').fetchall()]
            if 'original_price_idr' not in plan_columns:
                con.execute('ALTER TABLE plans ADD COLUMN original_price_idr INTEGER NOT NULL DEFAULT 0')
'''
        src=src.replace(marker,migration+marker,1)
    names=('RenewLicense','renew_existing_license','refresh_booth_signed_license')
    present={n.name for n in ast.parse(src).body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))}
    if any(n in present for n in names):
        raise ValueError('Fungsi perpanjangan sudah ada sebagian/seluruhnya; tidak menyisipkan duplikat.')
    marker='class LicenseStatus(BaseModel):'
    if marker not in src:raise ValueError('Titik penambahan API lisensi tidak cocok.')
    additions='\n'.join(part(ref,ast_node(ref,n)).rstrip('\n') for n in names)+'\n\n'
    src=src.replace(marker,additions+marker,1)
    ast.parse(src)
    return src

def patch_dashboard(src,ref):
    if 'id="licenseDays"' not in src or 'adminPlanEditor' not in src or 'adminLicenseRows' not in src:
        raise ValueError('Dashboard VPS tidak sesuai dengan struktur editor admin.')
    replacement=re.search(r'<input id="licenseDays"[^>]*><datalist id="durationPresets">.*?</datalist><small>.*?</small>',ref,re.S)
    if not replacement:raise ValueError('Input durasi sumber tidak ditemukan.')
    if '<select id="licenseDays"' in src:
        src,n=re.subn(r'<select id="licenseDays"[^>]*>.*?</select>',lambda m:replacement.group(),src,count=1,flags=re.S)
        if n!=1:raise ValueError('Penggantian durasi gagal.')
    elif 'list="durationPresets"' not in src:
        raise ValueError('Kontrol durasi tidak dikenal.')
    start_ref=ref.index(' // Harga manual:')
    end_ref=ref.index(" const t=$('adminLicenseRows');",start_ref)
    start=src.find(' for(const plan of planData.plans){')
    end=src.find(" const t=$('adminLicenseRows');",start)
    if min(start,end)<0:raise ValueError('Editor harga tidak cocok.')
    src=src[:start]+ref[start_ref:end_ref]+src[end:]
    if "const renew=node(" not in src:
        start_ref=ref.index('   const renew=node(')
        end_ref=ref.index(';t.append(tr)',start_ref)+len(';t.append(tr)')
        marker='};actions.append(btn);t.append(tr)'
        if marker not in src:raise ValueError('Tombol lisensi lama tidak cocok.')
        src=src.replace(marker,'};actions.append(btn);\n'+ref[start_ref:end_ref],1)
    src=src.replace('>Kelola Lisensi Perangkat</h2>','>Kelola & Perpanjang Lisensi Perangkat</h2>')
    for marker in ('Perpanjang','readRupiah','durationPresets','Harga Normal (Rp)'):
        if marker not in src:raise ValueError('UI belum lengkap: '+marker)
    return src

def main(apply):
    names=['cloud_control/server.py','cloud_control/web/cloud.html','cloud_control/web/paket.html']
    for p in names:
        if not (ROOT/p).is_file():raise FileNotFoundError('File produksi tidak ditemukan: '+p)
    old={p:(ROOT/p).read_text('utf-8') for p in names}
    backend=fetch('cloud_control/server.py')
    reference=fetch('cloud_control/web/index.html')
    new={names[0]:patch_server(old[names[0]],backend),
         names[1]:patch_dashboard(old[names[1]],reference),
         names[2]:fetch('cloud_control/web/paket.html')}
    for p in names:
        print(p, 'BERUBAH' if old[p]!=new[p] else 'TIDAK BERUBAH')
    if not apply:
        print('DRY RUN OK. Tidak ada perubahan di VPS. Lanjutkan dengan --apply.')
        return
    backup=Path('/opt/kaca-id/backups')/('pre-license-promo-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    for p in names:
        dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(old[p],'utf-8')
    try:
        for p in names:
            dest=ROOT/p
            temp=dest.with_suffix(dest.suffix+'.new')
            temp.write_text(new[p],'utf-8')
            temp.chmod(dest.stat().st_mode&0o777)
            temp.replace(dest)
    except Exception:
        for p in names:(ROOT/p).write_text(old[p],'utf-8')
        raise
    print('PATCH TERPASANG. Backup:',backup)
    print('Selanjutnya rebuild service kaca-cloud saja.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try: main(args.apply)
    except Exception as exc:
        print('PATCH DIBATALKAN:',exc,file=sys.stderr)
        sys.exit(1)
