# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1160, 640)
        self.rootLayout = QVBoxLayout(MainWindow)
        self.rootLayout.setObjectName(u"rootLayout")
        self.connGroup = QGroupBox(MainWindow)
        self.connGroup.setObjectName(u"connGroup")
        self.connLayout = QGridLayout(self.connGroup)
        self.connLayout.setObjectName(u"connLayout")
        self.portLabel = QLabel(self.connGroup)
        self.portLabel.setObjectName(u"portLabel")

        self.connLayout.addWidget(self.portLabel, 0, 0, 1, 1)

        self.portCombo = QComboBox(self.connGroup)
        self.portCombo.setObjectName(u"portCombo")

        self.connLayout.addWidget(self.portCombo, 0, 1, 1, 1)

        self.mockCheck = QCheckBox(self.connGroup)
        self.mockCheck.setObjectName(u"mockCheck")

        self.connLayout.addWidget(self.mockCheck, 0, 2, 1, 1)

        self.refreshButton = QPushButton(self.connGroup)
        self.refreshButton.setObjectName(u"refreshButton")

        self.connLayout.addWidget(self.refreshButton, 0, 3, 1, 1)

        self.connectButton = QPushButton(self.connGroup)
        self.connectButton.setObjectName(u"connectButton")

        self.connLayout.addWidget(self.connectButton, 0, 4, 1, 1)

        self.disconnectButton = QPushButton(self.connGroup)
        self.disconnectButton.setObjectName(u"disconnectButton")

        self.connLayout.addWidget(self.disconnectButton, 0, 5, 1, 1)

        self.testButton = QPushButton(self.connGroup)
        self.testButton.setObjectName(u"testButton")

        self.connLayout.addWidget(self.testButton, 0, 6, 1, 1)

        self.settingsButton = QPushButton(self.connGroup)
        self.settingsButton.setObjectName(u"settingsButton")

        self.connLayout.addWidget(self.settingsButton, 0, 7, 1, 1)


        self.rootLayout.addWidget(self.connGroup)

        self.statusGroup = QGroupBox(MainWindow)
        self.statusGroup.setObjectName(u"statusGroup")
        self.statusLayout = QHBoxLayout(self.statusGroup)
        self.statusLayout.setObjectName(u"statusLayout")
        self.stateLabel = QLabel(self.statusGroup)
        self.stateLabel.setObjectName(u"stateLabel")

        self.statusLayout.addWidget(self.stateLabel)

        self.interlockLabel = QLabel(self.statusGroup)
        self.interlockLabel.setObjectName(u"interlockLabel")

        self.statusLayout.addWidget(self.interlockLabel)

        self.limitLabel = QLabel(self.statusGroup)
        self.limitLabel.setObjectName(u"limitLabel")

        self.statusLayout.addWidget(self.limitLabel)

        self.statusSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.statusLayout.addItem(self.statusSpacer)

        self.stopAllButton = QPushButton(self.statusGroup)
        self.stopAllButton.setObjectName(u"stopAllButton")

        self.statusLayout.addWidget(self.stopAllButton)


        self.rootLayout.addWidget(self.statusGroup)

        self.stageGroup = QGroupBox(MainWindow)
        self.stageGroup.setObjectName(u"stageGroup")
        self.stageOuter = QVBoxLayout(self.stageGroup)
        self.stageOuter.setObjectName(u"stageOuter")
        self.jogSpeedLayout = QHBoxLayout()
        self.jogSpeedLayout.setObjectName(u"jogSpeedLayout")
        self.jogSpeedLabel = QLabel(self.stageGroup)
        self.jogSpeedLabel.setObjectName(u"jogSpeedLabel")

        self.jogSpeedLayout.addWidget(self.jogSpeedLabel)

        self.jogSpeedSpin = QDoubleSpinBox(self.stageGroup)
        self.jogSpeedSpin.setObjectName(u"jogSpeedSpin")

        self.jogSpeedLayout.addWidget(self.jogSpeedSpin)

        self.jogSpeedSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.jogSpeedLayout.addItem(self.jogSpeedSpacer)


        self.stageOuter.addLayout(self.jogSpeedLayout)

        self.stageContainer = QWidget(self.stageGroup)
        self.stageContainer.setObjectName(u"stageContainer")

        self.stageOuter.addWidget(self.stageContainer)


        self.rootLayout.addWidget(self.stageGroup)

        self.commandGroup = QGroupBox(MainWindow)
        self.commandGroup.setObjectName(u"commandGroup")
        self.commandLayout = QVBoxLayout(self.commandGroup)
        self.commandLayout.setObjectName(u"commandLayout")
        self.commandEdit = QPlainTextEdit(self.commandGroup)
        self.commandEdit.setObjectName(u"commandEdit")
        self.commandEdit.setMaximumSize(QSize(16777215, 68))

        self.commandLayout.addWidget(self.commandEdit)

        self.sendButton = QPushButton(self.commandGroup)
        self.sendButton.setObjectName(u"sendButton")

        self.commandLayout.addWidget(self.sendButton)


        self.rootLayout.addWidget(self.commandGroup)

        self.logGroup = QGroupBox(MainWindow)
        self.logGroup.setObjectName(u"logGroup")
        self.logLayout = QVBoxLayout(self.logGroup)
        self.logLayout.setObjectName(u"logLayout")
        self.logEdit = QPlainTextEdit(self.logGroup)
        self.logEdit.setObjectName(u"logEdit")
        self.logEdit.setReadOnly(True)

        self.logLayout.addWidget(self.logEdit)


        self.rootLayout.addWidget(self.logGroup)


        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"CP-700M \u30b3\u30f3\u30c8\u30ed\u30fc\u30e9", None))
        self.connGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u901a\u4fe1", None))
        self.portLabel.setText(QCoreApplication.translate("MainWindow", u"\u30dd\u30fc\u30c8", None))
        self.mockCheck.setText(QCoreApplication.translate("MainWindow", u"\u30b7\u30df\u30e5\u30ec\u30fc\u30b7\u30e7\u30f3", None))
        self.refreshButton.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u65b0", None))
        self.connectButton.setText(QCoreApplication.translate("MainWindow", u"\u63a5\u7d9a", None))
        self.disconnectButton.setText(QCoreApplication.translate("MainWindow", u"\u5207\u65ad", None))
        self.testButton.setText(QCoreApplication.translate("MainWindow", u"\u63a5\u7d9a\u30c6\u30b9\u30c8", None))
        self.settingsButton.setText(QCoreApplication.translate("MainWindow", u"\u8a2d\u5b9a\u2026", None))
        self.statusGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u72b6\u614b", None))
        self.stateLabel.setText(QCoreApplication.translate("MainWindow", u"\u672a\u63a5\u7d9a", None))
        self.interlockLabel.setText(QCoreApplication.translate("MainWindow", u"\u30a4\u30f3\u30bf\u30fc\u30ed\u30c3\u30af: -", None))
        self.limitLabel.setText(QCoreApplication.translate("MainWindow", u"\u30ea\u30df\u30c3\u30c8: -", None))
        self.stopAllButton.setText(QCoreApplication.translate("MainWindow", u"\u5168\u8ef8\u5373\u505c\u6b62", None))
        self.stageGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u30b9\u30c6\u30fc\u30b8\u64cd\u4f5c", None))
        self.jogSpeedLabel.setText(QCoreApplication.translate("MainWindow", u"\u30b8\u30e7\u30b0\u901f\u5ea6\uff08\u5168\u8ef8\u5171\u901a\uff09", None))
        self.commandGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u76f4\u63a5\u30b3\u30de\u30f3\u30c9", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"\u9001\u4fe1", None))
        self.logGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u30ed\u30b0", None))
    # retranslateUi

