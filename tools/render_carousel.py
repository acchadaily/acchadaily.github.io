import os,sys
from playwright.sync_api import sync_playwright
from PIL import Image
src=sys.argv[1]; pref=sys.argv[2]
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={'width':1080,'height':1350},device_scale_factor=2)
    pg.on('pageerror',lambda e:print('JS ERROR',e));pg.goto('file://'+os.path.abspath(src));pg.wait_for_timeout(1200)
    els=pg.locator('.s');n=els.count();outs=[]
    for i in range(n):
        f=f'{pref}_{i+1}.png';els.nth(i).screenshot(path=f)
        Image.open(f).convert('RGB').resize((1080,1350),Image.LANCZOS).save(f.replace('.png','.jpg'),quality=95);os.remove(f);outs.append(f.replace('.png','.jpg'))
    b.close()
ims=[Image.open(f).resize((360,450)) for f in outs]
s=Image.new('RGB',(360*len(ims),450),'white')
for i,im in enumerate(ims): s.paste(im,(i*360,0))
s.save(pref+'_sheet.jpg',quality=88);print(outs)
