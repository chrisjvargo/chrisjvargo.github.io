#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import threading
from dataclasses import asdict, dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


@dataclass
class PageCheck:
    path: str
    viewport: str
    screenshot: str
    title: str
    h1_count: int
    h2_count: int
    main: bool
    nav: bool
    skip_link: bool
    horizontal_overflow: bool
    visible_text_checks: dict[str, bool]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(dist: Path) -> tuple[ThreadingHTTPServer, str]:
    port = free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=str(dist))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def run_checks(dist: Path, out_dir: Path) -> list[PageCheck]:
    out_dir.mkdir(parents=True, exist_ok=True)
    server, base_url = start_server(dist)
    checks: list[PageCheck] = []
    viewports = {
        "desktop": {"width": 1366, "height": 900},
        "mobile": {"width": 390, "height": 844},
    }
    pages = {
        "home": {
            "path": "/",
            "required": [
                "Google Cloud AI work",
                "Research, teaching, and software for AI field readiness.",
                "AI Technical Enablement Proof",
                "socialcontext.ai",
            ],
            "forbidden": ["Portfolio Links", "Quick Links", "4,499 citations"],
        },
        "cv": {
            "path": "/cv/",
            "required": ["Curriculum Vitae", "Download CV (PDF)", "Education", "Master of Arts"],
            "forbidden": ["Pandoc HTML conversion is not available"],
        },
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for page_name, config in pages.items():
                    for viewport_name, viewport in viewports.items():
                        context = browser.new_context(viewport=viewport)
                        page = context.new_page()
                        url = base_url + config["path"]
                        page.goto(url, wait_until="networkidle")
                        screenshot = out_dir / f"{page_name}-{viewport_name}.png"
                        page.screenshot(path=screenshot, full_page=True)
                        visible_text = page.locator("body").inner_text()
                        normalized_visible_text = visible_text.casefold()
                        client_width = page.evaluate("document.documentElement.clientWidth")
                        scroll_width = page.evaluate("document.documentElement.scrollWidth")
                        checks.append(
                            PageCheck(
                                path=config["path"],
                                viewport=viewport_name,
                                screenshot=str(screenshot),
                                title=page.title(),
                                h1_count=page.locator("h1").count(),
                                h2_count=page.locator("h2").count(),
                                main=page.locator("main").count() == 1,
                                nav=page.locator("nav[aria-label='Primary']").count() == 1,
                                skip_link=page.locator("a.skip-link").count() == 1,
                                horizontal_overflow=scroll_width > client_width + 1,
                                visible_text_checks={
                                    **{
                                        f"required:{phrase}": phrase.casefold() in normalized_visible_text
                                        for phrase in config["required"]
                                    },
                                    **{
                                        f"forbidden_absent:{phrase}": phrase.casefold() not in normalized_visible_text
                                        for phrase in config["forbidden"]
                                    },
                                },
                            )
                        )
                        context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--out-dir", type=Path, default=Path("dv_publication/runtime/root_cv_screenshots"))
    parser.add_argument("--report", type=Path, default=Path("dv_publication/root_cv_visual_qa_report.json"))
    parser.add_argument("--manifest", type=Path, default=Path("dv_publication/root_cv_screenshot_manifest.csv"))
    args = parser.parse_args()
    checks = run_checks(args.dist, args.out_dir)
    errors = []
    for check in checks:
        if not check.main:
            errors.append(f"{check.path} {check.viewport}: missing single main landmark")
        if not check.nav:
            errors.append(f"{check.path} {check.viewport}: missing primary nav")
        if not check.skip_link:
            errors.append(f"{check.path} {check.viewport}: missing skip link")
        if check.horizontal_overflow:
            errors.append(f"{check.path} {check.viewport}: horizontal overflow")
        for label, ok in check.visible_text_checks.items():
            if not ok:
                errors.append(f"{check.path} {check.viewport}: failed text check {label}")
    payload = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "pages_checked": len(checks),
        "checks": [asdict(check) for check in checks],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    manifest_lines = ["path,page,viewport"]
    for check in checks:
        manifest_lines.append(f"{check.screenshot},{check.path},{check.viewport}")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    print(f"Wrote {args.manifest}")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
