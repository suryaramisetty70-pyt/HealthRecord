from playwright.sync_api import sync_playwright, expect
import uuid, io
from reportlab.pdfgen import canvas
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']); page=b.new_page(accept_downloads=True); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8765'); page.locator('[name=name]').fill('Fictional Patient'); page.locator('[name=email]').fill(uuid.uuid4().hex+'@example.com'); page.locator('[name=password]').fill('testpass123'); page.get_by_role('button',name='Register').click(); expect(page.locator('#msg')).to_contain_text('Registered'); page.get_by_role('button',name='Sign in').click(); expect(page.locator('#welcome')).to_contain_text('Fictional Patient'); print('PASS registration and login')
 page.locator('#records [name=title]').fill('Fictional checkup'); page.locator('#records [name=day]').fill('2026-11-24'); page.locator('#records [name=notes]').fill('Test only'); page.get_by_role('button',name='Save record').click(); expect(page.locator('#recordlist')).to_contain_text('Fictional checkup'); print('PASS record creation')
 page.locator('#vitals [name=day]').fill('2026-11-24');
 for k,v in dict(bp='120',glucose='95',cholesterol='180',pulse='70').items(): page.locator('#vitals [name='+k+']').fill(v)
 page.get_by_role('button',name='Save measurements').click(); expect(page.locator('#vcount')).to_have_text('1'); expect(page.locator('#chart circle')).to_have_count(1); print('PASS measurement and chart')
 f=io.BytesIO(); c=canvas.Canvas(f); c.drawString(50,700,'Fictional test'); c.save(); page.locator('input[type=file]').set_input_files({'name':'test.pdf','mimeType':'application/pdf','buffer':f.getvalue()}); page.get_by_role('button',name='Upload').click(); expect(page.locator('#doclist')).to_contain_text('test.pdf');
 with page.expect_download() as d: page.locator('#doclist a').click()
 assert d.value.path().read_bytes().startswith(b'%PDF'); print('PASS upload and download')
 with page.expect_download() as d: page.get_by_text('Download PDF summary').click()
 assert d.value.path().read_bytes().startswith(b'%PDF'); print('PASS PDF export')
 page.get_by_role('button',name='Run synthetic benchmark').click(); expect(page.locator('#mlresult')).to_contain_text('Synthetic test accuracy'); print('PASS synthetic ML benchmark')
 page.reload(); expect(page.locator('#recordlist')).to_contain_text('Fictional checkup'); page.on('dialog',lambda d:d.accept()); page.locator('#recordlist button').click(); expect(page.locator('#count')).to_have_text('0'); print('PASS persistence and deletion'); page.get_by_role('button',name='Sign out').click(); expect(page.locator('#auth')).to_be_visible(); assert not errors,errors; print('PASS logout; no uncaught browser errors'); b.close()
