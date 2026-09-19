# -*- coding: utf-8 -*-
"""
CNKI 批量导出 v6：按年份分段导出（突破知网 6000 条翻页上限）。
单浏览器会话跑完所有分段；每段独立检索；批次文件按 段+页范围 命名。
用法：.venv_dock/Scripts/python.exe scripts/32_cnki_export_v6_yearly.py [起始段序号]
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
from selenium.common.exceptions import StaleElementReferenceException

OUT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "cnki_raw"))
DBG = os.path.join(OUT, "debug")
PROG = os.path.join(OUT, "progress_v6.json")
QUERY = "SU=('高校'+'大学'+'高等学校'+'高等院校')*'实验室'*('安全'+'事故'+'风险'+'隐患'+'管理')"
SEGMENTS = [("2000-01-01", "2003-12-31"), ("2004-01-01", "2007-12-31"),
            ("2008-01-01", "2010-12-31")] + \
           [(f"{y}-01-01", f"{y}-12-31") for y in range(2011, 2027)]
BATCH_TRIGGER = 430


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
        try:
            els = [e for e in d.find_elements(By.XPATH, xp) if e.is_displayed()]
        except StaleElementReferenceException:
            time.sleep(1)
            continue
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
    return False


def selected_count(d):
    try:
        for e in d.find_elements(By.CSS_SELECTOR, "#selectCount"):
            t = (e.text or "").strip()
            if t.isdigit():
                return int(t)
    except Exception:
        pass
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


def page_ready(d):
    if "verify" in d.current_url:
        return False
    try:
        t = d.find_element(By.TAG_NAME, "body").text
        if "请完成安全验证" in t or "滑动完成验证" in t or "向右滑动" in t:
            return False
    except Exception:
        pass
    return bool(d.find_elements(By.XPATH, "//li[contains(text(),'专业检索')]"))


def wait_ready(d, timeout=1800):
    t0 = time.time()
    reminded = 0
    while time.time() - t0 < timeout:
        if page_ready(d):
            return True
        if time.time() - t0 > reminded:
            log("……等待页面就绪；若 Edge 中有滑块请拖动（任务栏找新 Edge 窗口）")
            reminded += 30
        time.sleep(2)
    raise RuntimeError("页面就绪等待超时")


def save_prog(seg_idx, page):
    with open(PROG, "w", encoding="utf-8") as f:
        json.dump({"seg": seg_idx, "page": page, "ts": time.strftime("%F %T")}, f)


def do_search(d, d1, d2):
    """按日期段检索并切到学术期刊、50条/页；返回总记录数"""
    d.get("https://kns.cnki.net/kns8s/AdvSearch?dbcode=CFLS")
    wait_ready(d)
    time.sleep(2)
    wait_visible(d, "//li[contains(text(),'专业检索')]", "专业检索tab", timeout=30)
    time.sleep(2)
    box = d.find_element(By.CSS_SELECTOR, "textarea")
    d.execute_script("arguments[0].value = arguments[1];", box, QUERY)
    d.execute_script("""
        var a=document.getElementById('datebox0'), b=document.getElementById('datebox1');
        if(a){a.removeAttribute('readonly'); a.value=arguments[0];}
        if(b){b.removeAttribute('readonly'); b.value=arguments[1];}
    """, d1, d2)
    js_click(d, d.find_element(By.CSS_SELECTOR, "input.search-btn"))
    log(f"检索 {d1}~{d2} ……")
    for i in range(30):
        time.sleep(2)
        if d.find_elements(By.CSS_SELECTOR, "input.cbItem") or "没有" in d.find_element(By.TAG_NAME, "body").text:
            break
    els = [e for e in d.find_elements(By.XPATH, "//*[contains(text(),'学术期刊')]") if e.is_displayed()]
    els = sorted(els, key=lambda e: len(e.text))
    if els:
        try:
            real_click(d, els[0])
        except Exception:
            js_click(d, els[0])
        for i in range(15):
            time.sleep(2)
            if d.find_elements(By.CSS_SELECTOR, "input.cbItem"):
                break
    for attempt in range(2):
        try:
            real_click(d, d.find_element(By.CSS_SELECTOR, "#perPageDiv .sort-default"))
            time.sleep(1.5)
            wait_visible(d, "//div[@id='perPageDiv']//*[text()='50']", "50条/页", required=False)
            for i in range(15):
                time.sleep(2)
                if len(d.find_elements(By.CSS_SELECTOR, "input.cbItem")) == 50:
                    break
            if len(d.find_elements(By.CSS_SELECTOR, "input.cbItem")) == 50:
                break
        except Exception as e:
            log("页大小设置失败（重试）:", e)
    total = result_total(d)
    rows = len(d.find_elements(By.CSS_SELECTOR, "input.cbItem"))
    log(f"段 {d1[:4]}—{d2[:4]}：总记录 {total}，每页 {rows}")
    return total, rows


def jump_to_page(d, target):
    page = 1
    while page < target:
        if not wait_visible(d, "//a[contains(text(),'下一页') or @id='PageNext' or @id='Page_next_top']", "下一页", timeout=8, required=False):
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
    for el in d.find_elements(By.CSS_SELECTOR, "input[name='selectCheckbox']"):
        try:
            if not el.is_selected():
                js_click(d, el)
        except Exception:
            pass
    time.sleep(3)
    eat_alert(d)
    cnt = selected_count(d)
    if cnt is not None and cnt > before:
        done = True
    if not done:
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
    if cnt is not None and cnt < before + len(cbs):
        for cb in cbs:
            if not cb.is_selected():
                js_click(d, cb)
                time.sleep(0.25)
        time.sleep(3)
        eat_alert(d)
        cnt = selected_count(d)
    return len(cbs), cnt


def clear_selection(d):
    for attempt in range(4):
        clicked = False
        for sel in ["a[href*='filenameClear']", "a.btn-clear-selected", "a.btn-clearall", "a.clearall"]:
            els = [e for e in d.find_elements(By.CSS_SELECTOR, sel) if e.is_displayed()]
            if els:
                try:
                    real_click(d, els[0])
                except Exception:
                    js_click(d, els[0])
                clicked = True
                break
        if not clicked:
            for sel in ["a[href*='filenameClear']", "a.btn-clear-selected", "a.btn-clearall", "a.clearall"]:
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
    raise RuntimeError("清除已选失败")


def export_batch(d, tag, page_start, page_end):
    ok = False
    for attempt in range(3):
        wait_visible(d, "//a[contains(text(),'导出与分析')]", "导出与分析")
        time.sleep(2)
        eat_alert(d)
        try:
            wait_visible(d, "//*[contains(text(),'导出文献')]", "导出文献", timeout=15)
            ok = True
            break
        except RuntimeError:
            log(f"  导出文献菜单未展开，重试 {attempt+1}")
            eat_alert(d)
    if not ok:
        raise RuntimeError("导出文献菜单未展开")
    time.sleep(1.5)
    eat_alert(d)
    wait_visible(d, "//*[contains(text(),'Refworks') or contains(text(),'RefWorks')]", "Refworks")
    t0 = time.time()
    while len(d.window_handles) < 2 and time.time() - t0 < 15:
        time.sleep(1.5)
    if len(d.window_handles) < 2:
        wait_visible(d, "//*[contains(text(),'Refworks') or contains(text(),'RefWorks')]", "Refworks-重试")
        t0 = time.time()
        while len(d.window_handles) < 2 and time.time() - t0 < 15:
            time.sleep(1.5)
    if len(d.window_handles) > 1:
        d.switch_to.window(d.window_handles[-1])
    # 等导出按钮（导出页可能弹内嵌验证，等人工）
    t0 = time.time()
    while time.time() - t0 < 1800:
        try:
            if d.find_elements(By.XPATH, "//a[contains(text(),'导出')]|//button[contains(text(),'导出')]|//input[@value='导出']"):
                break
            t = d.find_element(By.TAG_NAME, "body").text
            if "安全验证" in t or "滑动" in t or "verify" in d.current_url:
                if int(time.time() - t0) % 30 < 2:
                    log("  导出页出现验证，请人工完成……")
        except Exception:
            pass
        time.sleep(2)
    else:
        raise RuntimeError("导出页就绪超时")
    before = set(glob.glob(os.path.join(OUT, "CNKI-*.txt")))
    got = None
    for attempt in range(3):
        wait_visible(d, "//a[contains(text(),'导出')]|//button[contains(text(),'导出')]|//input[@value='导出']", "导出按钮")
        for i in range(20):
            time.sleep(2)
            new = set(glob.glob(os.path.join(OUT, "CNKI-*.txt"))) - before
            if new:
                got = new.pop()
                break
        if got:
            break
        log(f"  下载未成功，第 {attempt+1} 次重新点导出")
        time.sleep(5)
    if got:
        dst = os.path.join(OUT, f"seg_{tag}_p{page_start:04d}_{page_end:04d}.txt")
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(got, dst)
        n = sum(1 for line in open(dst, encoding="utf-8", errors="ignore") if line.startswith("RT "))
        log(f"★ 导出 {dst.split(os.sep)[-1]}（{n} 条）")
    else:
        raise RuntimeError("下载三次均失败")
    if len(d.window_handles) > 1:
        d.close()
        d.switch_to.window(d.window_handles[0])
    time.sleep(1)


def main():
    seg_start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    o = Options()
    o.add_argument("--start-maximized")
    o.add_argument("--user-data-dir=" + os.path.join(OUT, "edge_profile"))
    o.page_load_strategy = "eager"
    o.add_experimental_option("prefs", {
        "download.default_directory": OUT,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False,
        "safebrowsing.disable_download_protection": True})
    log("启动 Edge……")
    d = webdriver.Edge(options=o)
    d.set_page_load_timeout(120)
    try:
        d.set_window_position(0, 0)
        d.maximize_window()
    except Exception:
        pass
    log("Edge 已启动")
    only = len(sys.argv) > 2 and sys.argv[2] == "only"
    seg_iter = [(seg_start, SEGMENTS[seg_start])] if only else [(si, x) for si, x in enumerate(SEGMENTS) if si >= seg_start]
    try:
        for si, (d1, d2) in seg_iter:
            log(f"===== 段 {si}: {d1[:4]}—{d2[:4]} =====")
            total, rows = do_search(d, d1, d2)
            if not total:
                log("本段无记录或读取失败，跳过")
                continue
            total_pages = math.ceil(total / (rows or 50))
            page = 1
            pool = 0
            batch_start = 1
            fails = 0
            while page <= total_pages:
                if not page_ready(d):
                    wait_ready(d)
                if is_throttled(d):
                    log(f"!!! 限流（段{si} 第{page}页），休息150秒重搜跳回")
                    save_prog(si, page)
                    time.sleep(150)
                    do_search(d, d1, d2)
                    jump_to_page(d, page)
                    pool = selected_count(d) or 0
                    continue
                if pool >= BATCH_TRIGGER:
                    try:
                        export_batch(d, f"{d1[:4]}", batch_start, page)
                    except Exception as e:
                        log(f"!!! 导出失败（段{si} {batch_start}-{page}）: {e}")
                        try:
                            fb = json.load(open(os.path.join(OUT, "failed_batches.json"), encoding="utf-8"))
                        except Exception:
                            fb = []
                        fb.append({"seg": si, "d1": d1, "d2": d2, "p0": batch_start, "p1": page, "ts": time.strftime("%F %T")})
                        json.dump(fb, open(os.path.join(OUT, "failed_batches.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                        do_search(d, d1, d2)
                        clear_selection(d)
                        jump_to_page(d, batch_start)
                        page = batch_start
                        pool = 0
                        continue
                    clear_selection(d)
                    batch_start = page + 1
                    pool = 0
                    for cb in d.find_elements(By.CSS_SELECTOR, "input.cbItem"):
                        try:
                            if cb.is_selected():
                                js_click(d, cb)
                        except Exception:
                            pass
                    time.sleep(2)
                    eat_alert(d)
                    continue
                n_sel, cnt = select_page(d)
                if n_sel == 0:
                    fails += 1
                    log(f"!!! 段{si} 第{page}页无结果行（{fails}/3）")
                    if fails >= 3:
                        snap(d, f"empty_s{si}_p{page}")
                        break
                    time.sleep(30)
                    do_search(d, d1, d2)
                    jump_to_page(d, page)
                    pool = selected_count(d) or 0
                    continue
                fails = 0
                if pool == 0:
                    batch_start = page
                pool = cnt if cnt is not None else pool + n_sel
                log(f"段{si} 第{page}/{total_pages}页 +{n_sel}，已选={pool}")
                save_prog(si, page)
                if not wait_visible(d, "//a[contains(text(),'下一页') or @id='PageNext' or @id='Page_next_top']", "下一页", timeout=10, required=False):
                    log("本段最后一页")
                    break
                page += 1
                time.sleep(random.uniform(5.0, 8.0))
            # 段尾批
            if pool > 0:
                try:
                    export_batch(d, f"{d1[:4]}", batch_start, page)
                    clear_selection(d)
                except Exception as e:
                    log(f"!!! 段尾批导出失败（段{si}）: {e}")
            save_prog(si + 1, 1)
            time.sleep(random.uniform(5, 10))
        log("=== 全部段完成 ===")
        time.sleep(30)
    except Exception as e:
        log("!!! 异常终止:", e)
        snap(d, "fatal_v6")
        raise
    finally:
        d.quit()


if __name__ == "__main__":
    main()
