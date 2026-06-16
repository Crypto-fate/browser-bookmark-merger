#!/usr/bin/env python3
"""
比较两个浏览器书签文件的差异
"""
import re
from html.parser import HTMLParser
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse, unquote


class BookmarkParser(HTMLParser):
    """解析 Netscape Bookmark 格式"""

    def __init__(self):
        super().__init__()
        self.folder_stack = []      # 当前文件夹路径栈
        self.current_folder = None
        self.bookmarks = []         # (folder_path, title, url, add_date, icon)
        self.folders = []           # (folder_path, add_date, last_modified)
        self.in_h3 = False
        self.in_a = False
        self.current_attrs = {}
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "h3":
            self.in_h3 = True
            self.current_text = ""
            self.current_attrs = attrs_dict
        elif tag == "a":
            self.in_a = True
            self.current_text = ""
            self.current_attrs = attrs_dict
            # 进入子目录前，关闭上一级文件夹标记
            # 真正的文件夹推进由 end_h3 处理

    def handle_endtag(self, tag):
        if tag == "h3" and self.in_h3:
            name = self.current_text.strip()
            self.folders.append((tuple(self.folder_stack), name, self.current_attrs))
            self.folder_stack.append(name)
            self.current_folder = "/".join(self.folder_stack)
            self.in_h3 = False
        elif tag == "a" and self.in_a:
            href = self.current_attrs.get("href", "").strip()
            title = self.current_text.strip()
            if href:
                add_date = self.current_attrs.get("add_date", "")
                icon = "yes" if "icon" in self.current_attrs else ""
                self.bookmarks.append({
                    "folder": self.current_folder or "(root)",
                    "title": title,
                    "url": href,
                    "add_date": add_date,
                    "icon": icon,
                })
            self.in_a = False
        elif tag == "dl":
            # 离开当前目录
            if self.folder_stack:
                self.folder_stack.pop()
            self.current_folder = "/".join(self.folder_stack) if self.folder_stack else None

    def handle_data(self, data):
        if self.in_h3 or self.in_a:
            self.current_text += data


def parse_file(path):
    content = Path(path).read_text(encoding="utf-8", errors="ignore")
    parser = BookmarkParser()
    parser.feed(content)
    return parser.bookmarks


def norm_url(u):
    """URL 归一化：去末尾斜杠、小写 host、unquote"""
    u = unquote(u.strip())
    if not u:
        return u
    p = urlparse(u)
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = p.path.rstrip("/") if p.path != "/" else ""
    qs = p.query
    # 一些常见 query 参数顺序差异
    return f"{scheme}://{netloc}{path}{('?' + qs) if qs else ''}"


def main():
    file1 = "/Users/zhangzhifa/Downloads/书签.html"
    file2 = "/Users/zhangzhifa/Downloads/bookmarks_2026_6_16.html"

    bks1 = parse_file(file1)
    bks2 = parse_file(file2)

    print(f"=== 文件 1: 书签.html ===")
    print(f"  书签总数: {len(bks1)}")
    print(f"=== 文件 2: bookmarks_2026_6_16.html ===")
    print(f"  书签总数: {len(bks2)}")

    # 统计文件夹
    folders1 = defaultdict(int)
    folders2 = defaultdict(int)
    for b in bks1:
        folders1[b["folder"]] += 1
    for b in bks2:
        folders2[b["folder"]] += 1

    print(f"\n=== 文件 1 文件夹结构 ===")
    for f, c in sorted(folders1.items()):
        print(f"  [{c:3d}] {f}")
    print(f"\n=== 文件 2 文件夹结构 ===")
    for f, c in sorted(folders2.items()):
        print(f"  [{c:3d}] {f}")

    # 按归一化 URL 索引
    by_url1 = {norm_url(b["url"]): b for b in bks1}
    by_url2 = {norm_url(b["url"]): b for b in bks2}

    urls1 = set(by_url1.keys())
    urls2 = set(by_url2.keys())

    only_in_1 = urls1 - urls2
    only_in_2 = urls2 - urls1
    common = urls1 & urls2

    print(f"\n=== URL 集合对比 (按归一化) ===")
    print(f"  仅在文件 1: {len(only_in_1)}")
    print(f"  仅在文件 2: {len(only_in_2)}")
    print(f"  共有:       {len(common)}")

    print(f"\n--- 仅在【书签.html】中的书签 ---")
    for u in sorted(only_in_1):
        b = by_url1[u]
        print(f"  [{b['folder']}] {b['title']}  -> {b['url']}")

    print(f"\n--- 仅在【bookmarks_2026_6_16.html】中的书签 ---")
    for u in sorted(only_in_2):
        b = by_url2[u]
        print(f"  [{b['folder']}] {b['title']}  -> {b['url']}")

    # 共有但归属文件夹不同
    print(f"\n--- 共有但【所在文件夹不同】的书签 ---")
    folder_diff = []
    for u in common:
        if by_url1[u]["folder"] != by_url2[u]["folder"]:
            folder_diff.append((u, by_url1[u], by_url2[u]))
    for u, b1, b2 in folder_diff:
        print(f"  {u}")
        print(f"     文件1: [{b1['folder']}]  {b1['title']}")
        print(f"     文件2: [{b2['folder']}]  {b2['title']}")

    # 共有但标题不同
    print(f"\n--- 共有但【标题不同】的书签 ---")
    title_diff = []
    for u in common:
        if by_url1[u]["title"] != by_url2[u]["title"]:
            title_diff.append((u, by_url1[u], by_url2[u]))
    for u, b1, b2 in title_diff:
        print(f"  {u}")
        print(f"     文件1: {b1['title']!r}")
        print(f"     文件2: {b2['title']!r}")


if __name__ == "__main__":
    main()
