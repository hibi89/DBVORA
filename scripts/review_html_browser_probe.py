"""Optional Chromium smoke of the actual offline archive review HTML renderer.

This is document-only Playwright testing (set_content), NOT verified file://
navigation, customer output or Windows package acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from dbvora.archive.review_html import ReviewError, render


def _synthetic() -> dict:
    return {'contract_version':'dbvora.synthetic.request-reconcile.v1',
            'inspection_mode':'read_only_human_review_only', 'request_count':3,
            'counts':{'INTERRUPTED_REVIEW_REQUIRED':1,
                      'RECORDED_MATCH_REVIEW_REQUIRED':1,
                      'RECORDED_NOT_VERIFIED':1,
                      'DUPLICATE_ARTIFACT_REVIEW_REQUIRED':0},
            'unmatched_verified_archive_count':2,
            'may_resume_archive':False,'exactly_once_verified':False,
            'authenticity_verified':False,'power_loss_verified':False,
            'ready_for_customer_data':False}


def probe(chromium: str | None = None) -> dict:
    report={'status':'NOT_RUN','scope':'SYNTHETIC_DOCUMENT_ONLY',
            'browser_native_file_url_verified':False,
            'windows_browser_verified':False,'customer_ready':False,
            'checks':0}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        report['reason']='PLAYWRIGHT_UNAVAILABLE'
        return report
    executable=chromium or shutil.which('chromium') or shutil.which('chromium-browser')
    if not executable or not Path(executable).is_file():
        report['reason']='CHROMIUM_UNAVAILABLE'
        return report
    try:
        html=render(_synthetic()).decode('utf-8')
        with sync_playwright() as engine:
            browser=engine.chromium.launch(executable_path=executable,headless=True,
                                           args=['--no-sandbox','--disable-dev-shm-usage'])
            try:
                page=browser.new_page(viewport={'width':1024,'height':768})
                network,errors,dialogs=[],[],[]
                page.on('request',lambda r:network.append('request'))
                page.on('pageerror',lambda e:errors.append('pageerror'))
                page.on('dialog',lambda d:(dialogs.append('dialog'),d.dismiss()))
                page.set_content(html,wait_until='load')
                checks=[
                    page.locator('html').get_attribute('lang')=='ko',
                    page.locator('table tbody tr').count()==5,
                    page.locator('table thead th').count()==2,
                    page.locator('table caption').count()==1,
                    '복구 승인 아님' in page.locator('main').inner_text(),
                    '중단된 요청' in page.locator('table').inner_text(),
                    page.locator('button,form,input,script,iframe').count()==0,
                    page.locator('a[href],img,link[rel=stylesheet]').count()==0,
                    'Content-Security-Policy' in html and "default-src 'none'" in html,
                    len(network)==len(errors)==len(dialogs)==0,
                    page.locator('h1').count()==1,
                    page.locator('table tbody tr').last.locator('td').inner_text().strip()=='2',
                ]
                report['checks']=sum(checks)
                report['status']='PASS_SYNTHETIC_DOCUMENT_ONLY' if all(checks) else 'FAIL_CLOSED'
            finally:
                browser.close()
    except (ReviewError, OSError, ValueError, TypeError):
        report['status']='FAIL_CLOSED'
        report['reason']='BROWSER_PROBE_FAILED'
    except Exception:
        report['status']='FAIL_CLOSED'
        report['reason']='UNEXPECTED_BROWSER_PROBE_FAILURE'
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description='Optional local Chromium static review HTML probe')
    parser.add_argument('--chromium')
    args=parser.parse_args(argv)
    result=probe(args.chromium)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS_SYNTHETIC_DOCUMENT_ONLY' else 1


if __name__=='__main__':
    raise SystemExit(main())
