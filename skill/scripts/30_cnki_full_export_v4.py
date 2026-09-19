# -*- coding: utf-8 -*-
"""
CNKI 批量导出 v4（阶段4）：学术期刊约 18,300 条。
v4：菜单点击全部改为显式等待（WebDriverWait 式轮询）；批次按"已选记录数≥460"触发（适配任意页大小）；
    清除后强制校验；页大小设置后核验行数；总页数动态解析。
用法：.venv_dock/Scripts/python.exe scripts/30_cnki_full_export_v4.py [起始页码]
"""
import glob
import json
import math
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import random
import re
import sys
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

OUT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "cnki_raw"))
DBG = os.path.join(OUT, "debug")
PROG = os.path.join(OUT, "progress.json")
QUERY = "SU=('高校'+'大学'+'高等学校'+'高等院校')*'实验室'*('安全'+'事故'+'风险'+'隐患'+'管理')"
BATCH_TRIGGER = 460  # 已选达到此值即导出（远离500上限）


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def snap(d, name):
    try:
        with open(os.path.join(DBG, name + ".html"), "w", encoding="utf-8") as f:
            f.write(d.page_source)
        d.save_screenshot(os.path.join(DBG, name + ".png"))
    except Exception:
        pass


def eat_alert(d):
    try:
        d.switch_to.alert.accept()
        log("（已关闭弹窗）")
        time.sleep(1)
    except Exception:
        pass


def js_click(d, el):
    d.execute_script("arguments[0].click();", el)


def real_click(d, el):
    ActionChains(d).move_to_element(el).pause(0.2).click(el).perform()


def wait_visible(d, xp, label, timeout=12, required=True):
    t0 = time.time()
    while time.time() - t0 < timeout:
        els = [e for e in d.find_elements(By.XPATH, xp) if e.is_displayed()]
        if els:
            try:
                real_click(d, els[0])
            except Exception:
                js_click(d, els[0])
            log(f"点击 {label}")
            return True
        time.sleep(0.8)
    if required:
        snap(d, "missing_" + re.sub(r"\W", "", label))
        raise RuntimeError(f"等待可见元素超时: {label}")
    log(f"跳过(未找到) {label}")
    return False


def selected_count(d):
    try:
        m = re.search(r"已选\s*(\d+)", d.find_element(By.TAG_NAME, "body").text)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def result_total(d):
    try:
        m = re.search(r"共找到\s*([\d,]+)\s*条结果", d.find_element(By.TAG_NAME, "body").text)
        return int(m.group(1).replace(",", "")) if m else None
    except Exception:
        return None


def is_throttled(d):
    try:
        t = d.find_element(By.TAG_NAME, "body").text
        return "暂无数据" in t or "请稍后重试" in t
    except Exception:
        return False


def captcha_guard(d):
    eat_alert(d)
    if "verify" in d.current_url:
        log("!!! 验证码，请人工完成……")
        t0 = time.time()
        while time.time() - t0 < 1800:
            if "verify" not in d.current_url:
                log(">>> 验证通过，继续")
                time.sleep(2)
                return True
            time.sleep(2)
        raise RuntimeError("验证码等待超时")
    return True


def save_prog(page):
    with open(PROG, "w", encoding="utf-8") as f:
        json.dump({"page": page, "ts": time.strftime("%F %T")}, f)


def do_search(d):
    d.get("https://kns.cnki.net/kns8s/AdvSearch?dbcode=CFLS")
    t0 = time.time()
    while time.time() - t0 < 1800:
        if "verify" not in d.current_url:
            break
        time.sleep(2)
    time.sleep(2)
    wait_visible(d, "//li[contains(text(),'专业检索')]", "专业检索tab")
    time.sleep(2)
    box = d.find_element(By.CSS_SELECTOR, "textarea")
    d.execute_script("arguments[0].value = arguments[1];", box, QUERY)
    d.execute_script("""
        var a=document.getElementById('datebox0'), b=document.getElementById('datebox1');
        if(a){a.removeAttribute('readonly'); a.value='2000-01-01';}
        if(b){b.removeAttribute('readonly'); b.value='2026-12-31';}
    """)
    js_click(d, d.find_element(By.CSS_SELECTOR, "input.search-btn"))
    log("检索中……")
    for i in range(30):
        time.sleep(2)
        if d.find_elements(By.CSS_SELECTOR, "input.cbItem"):
            break
    els = [e for e in d.find_elements(By.XPATH, "//*[contains(text(),'学术期刊')]") if e.is_displayed()]
    els = sorted(els, key=lambda e: len(e.text))
    if els:
        try:
            real_click(d, els[0])
        except Exception:
            js_click(d, els[0])
        log("已点 学术期刊")
        for i in range(15):
            time.sleep(2)
            if d.find_elements(By.CSS_SELECTOR, "input.cbItem"):
                break
    # 设 50/页并核验
    try:
        real_click(d, d.find_element(By.CSS_SELECTOR, "#perPageDiv .sort-default"))
        time.sleep(1.5)
        wait_visible(d, "//div[@id='perPageDiv']//*[text()='50']", "50条/页", required=False)
        for i in range(15):
            time.sleep(2)
            n = len(d.find_elements(By.CSS_SELECTOR, "input.cbItem"))
            if n == 50:
                break
        log("当前页行数:", len(d.find_elements(By.CSS_SELECTOR, "input.cbItem")))
    except Exception as e:
        log("页大小设置失败（按当前页大小继续）:", e)


def jump_to_page(d, target):
    page = 1
    while page < target:
        captcha_guard(d)
        if not wait_visible(d, "//a[contains(text(),'下一页') or @id='PageNext']", "下一页", timeout=8, required=False):
            return False
        page += 1
        time.sleep(random.uniform(2.5, 4.0))
    return True


def select_page(d):
    cbs = [e for e in d.find_elements(By.CSS_SELECTOR, "input.cbItem") if e.is_displayed()]
    if not cbs:
        return 0, None
    before = selected_count(d) or 0
    done = False
    for el in d.find_elements(By.CSS_SELECTOR, "a.selectall"):
        try:
            js_click(d, el)
        except Exception:
            pass
    time.sleep(3)
    eat_alert(d)
    cnt = selected_count(d)
    if cnt is not None and cnt > before:
        done = True
    if not done:
        log("  全选无效，逐框勾选")
        for cb in cbs:
            if not cb.is_selected():
                js_click(d, cb)
                time.sleep(0.2)
        time.sleep(3)
        eat_alert(d)
        cnt = selected_count(d)
    # 补缺
    if cnt is not None and cnt < before + len(cbs):
        for cb in cbs:
            if not cb.is_selected():
                js_click(d, cb)
                time.sleep(0.25)
        time.sleep(3)
        eat_alert(d)
        cnt = selected_count(d)
    return len(cbs), cnt


CLEAR_SELS = ["a.btn-clear-selected", "a.btn-clearall", "a.clearall"]


def clear_selection(d):
    for attempt in range(4):
        clicked = False
        for sel in CLEAR_SELS:
            els = [e for e in d.find_elements(By.CSS_SELECTOR, sel) if e.is_displayed()]
            if els:
                try:
                    real_click(d, els[0])
                except Exception:
                    js_click(d, els[0])
                clicked = True
                break
        if not clicked:
            for sel in CLEAR_SELS:
                for e in d.find_elements(By.CSS_SELECTOR, sel):
                    try:
                        js_click(d, e)
                        clicked = True
                    except Exception:
                        pass
        time.sleep(1.5)
        eat_alert(d)
        time.sleep(2)
        cnt = selected_count(d)
        if cnt in (0, None):
            log("已选已清除")
            return True
        log(f"  清除后已选={cnt}，重试 {attempt+1}")
    raise RuntimeError("清除已选失败，停止以防脏数据")


def export_batch(d, batch_no):
    wait_visible(d, "//a[contains(text(),'导出与分析')]", "导出与分析")
    time.sleep(1.5)
    eat_alert(d)
    wait_visible(d, "//*[contains(text(),'导出文献')]", "导出文献")
    time.sleep(1.5)
    eat_alert(d)
    wait_visible(d, "//*[contains(text(),'Refworks') or contains(text(),'RefWorks')]", "Refworks")
    time.sleep(6)
    if len(d.window_handles) > 1:
        d.switch_to.window(d.window_handles[-1])
    before = set(glob.glob(os.path.join(OUT, "CNKI-*.txt")))
    wait_visible(d, "//a[contains(text(),'导出')]|//button[contains(text(),'导出')]|//input[@value='导出']", "导出按钮")
    got = None
    for i in range(20):
        time.sleep(2)
        new = set(glob.glob(os.path.join(OUT, "CNKI-*.txt"))) - before
        if new:
            got = new.pop()
            break
    if got:
        dst = os.path.join(OUT, f"batch_{batch_no:03d}.txt")
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(got, dst)
        n = sum(1 for line in open(dst, encoding="utf-8", errors="ignore") if line.startswith("RT "))
        log(f"★ 批次 {batch_no} 完成（{n} 条）")
    else:
        snap(d, f"batch_{batch_no:03d}_nodownload")
        log(f"!!! 批次 {batch_no} 未检测到下载")
    if len(d.window_handles) > 1:
        d.close()
        d.switch_to.window(d.window_handles[0])
    time.sleep(1)


def main():
    page = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    o = Options()
    o.add_argument("--start-maximized")
    o.add_experimental_option("prefs", {"download.default_directory": OUT, "download.prompt_for_download": False})
    d = webdriver.Edge(options=o)
    batch_no = 1
    try:
        do_search(d)
        total = result_total(d) or 18300
        rows0 = len(d.find_elements(By.CSS_SELECTOR, "input.cbItem")) or 20
        total_pages = math.ceil(total / rows0)
        log(f"总记录 {total}，每页 {rows0}，总页数 {total_pages}")
        if page > 1:
            batch_no = (page - 1) // 10 + 1
            jump_to_page(d, page)
        records_in_batch = 0
        fails = 0
        while page <= total_pages:
            captcha_guard(d)
            if is_throttled(d):
                log(f"!!! 限流态（第 {page} 页），休息 150 秒重搜跳回")
                save_prog(page)
                time.sleep(150)
                do_search(d)
                jump_to_page(d, page)
                records_in_batch = 0
                continue
            n_sel, cnt = select_page(d)
            if n_sel == 0:
                fails += 1
                log(f"!!! 第 {page} 页无结果行（{fails}/3）")
                if fails >= 3:
                    snap(d, f"empty_p{page}")
                    break
                time.sleep(30)
                do_search(d)
                jump_to_page(d, page)
                continue
            fails = 0
            records_in_batch += n_sel
            log(f"第 {page}/{total_pages} 页 +{n_sel}，已选={cnt}，批内 {records_in_batch}")
            save_prog(page)
            if records_in_batch >= BATCH_TRIGGER:
                export_batch(d, batch_no)
                clear_selection(d)
                batch_no += 1
                records_in_batch = 0
                time.sleep(random.uniform(6, 10))
            if not wait_visible(d, "//a[contains(text(),'下一页') or @id='PageNext']", "下一页", timeout=10, required=False):
                log("最后一页或翻页失败")
                break
            page += 1
            time.sleep(random.uniform(5.0, 8.0))
        if records_in_batch > 0:
            export_batch(d, batch_no)
            clear_selection(d)
        save_prog(page)
        log("=== 全部完成 ===")
        time.sleep(30)
    except Exception as e:
        log("!!! 异常终止:", e)
        snap(d, "fatal")
        save_prog(page)
        raise
    finally:
        d.quit()


if __name__ == "__main__":
    main()
