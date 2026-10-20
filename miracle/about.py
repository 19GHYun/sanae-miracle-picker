# -*- coding: utf-8 -*-
"""ⓘ 정보 창: 버전 · 공정성 · 단축키 · 데이터 폴더 · 저장소 링크 · 2차 창작 고지."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .i18n import T

REPO = "https://github.com/19GHYun/sanae-miracle-picker"


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, version: str, folder: Path):
        super().__init__(parent)
        self.folder = folder
        self.setWindowTitle(T("정보"))
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 16)
        v.setSpacing(10)
        self.text = QLabel(self.html(title, version), objectName="about")
        self.text.setTextFormat(Qt.RichText)
        self.text.setWordWrap(True)
        self.text.setOpenExternalLinks(True)
        self.text.setTextInteractionFlags(Qt.TextBrowserInteraction)
        v.addWidget(self.text)
        row = QHBoxLayout()
        open_btn = QPushButton(T("📁 데이터 폴더 열기"), objectName="small")
        open_btn.clicked.connect(self.open_folder)
        close = QPushButton(T("닫기"), objectName="small")
        close.clicked.connect(self.accept)
        close.setDefault(True)
        row.addWidget(open_btn)
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)

    @staticmethod
    def html(title: str, version: str) -> str:
        lines = [
            f"<h2 style='color:#2E9E5B; margin:0'>{title}</h2>",
            f"<p style='color:#6B7F72; margin-top:2px'>v{version}</p>",
            "<p>" + T("모리야 신사의 무녀 코치야 사나에가 기적을 일으켜 뽑아 주는 추첨 프로그램이에요.") + "</p>",
            "<p><b>" + T("공정성") + "</b> — " + T("모든 추첨은 운영체제의 안전한 난수로 만든 시드 하나로 정해지고 기록에 남아요. "
                                                "같은 목록 · 같은 시드면 언제 다시 해도 같은 결과예요.") + "</p>",
            "<p><b>" + T("단축키") + "</b> — Space · Ctrl+Enter · F5: " + T("기적을 일으키기 · 다음 발표 · 바로 결과") + "</p>",
            "<p><b>" + T("개인정보") + "</b> — " + T("인터넷을 쓰지 않아요. 목록 · 기록 · 설정은 이 PC 의 데이터 폴더에만 저장돼요.") + "</p>",
            f"<p><a href='{REPO}' style='color:#3D5BA9'>GitHub</a> — " + T("새 버전 · 사용법 · 문의") + "</p>",
            "<p style='color:#6B7F72; font-size:11px'>" + T("동방 프로젝트(상하이 앨리스 환악단)의 비공식 2차 창작입니다. 소스 코드는 MIT 라이선스.") + "</p>",
        ]
        return "".join(lines)

    def open_folder(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(self.folder))
