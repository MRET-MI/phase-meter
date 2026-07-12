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

        self.triggerButton = QPushButton(self.connGroup)
        self.triggerButton.setObjectName(u"triggerButton")

        self.connLayout.addWidget(self.triggerButton, 0, 8, 1, 1)


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

        self.fileGroup = QGroupBox(MainWindow)
        self.fileGroup.setObjectName(u"fileGroup")
        self.fileLayout = QVBoxLayout(self.fileGroup)
        self.fileLayout.setObjectName(u"fileLayout")
        self.fileTopRow = QHBoxLayout()
        self.fileTopRow.setObjectName(u"fileTopRow")
        self.targetSelLabel = QLabel(self.fileGroup)
        self.targetSelLabel.setObjectName(u"targetSelLabel")

        self.fileTopRow.addWidget(self.targetSelLabel)

        self.targetCombo = QComboBox(self.fileGroup)
        self.targetCombo.setObjectName(u"targetCombo")
        self.targetCombo.setEditable(True)
        self.targetCombo.setInsertPolicy(QComboBox.NoInsert)
        self.targetCombo.setMinimumWidth(220)

        self.fileTopRow.addWidget(self.targetCombo)

        self.targetModeLabel = QLabel(self.fileGroup)
        self.targetModeLabel.setObjectName(u"targetModeLabel")

        self.fileTopRow.addWidget(self.targetModeLabel)

        self.targetModeCombo = QComboBox(self.fileGroup)
        self.targetModeCombo.setObjectName(u"targetModeCombo")

        self.fileTopRow.addWidget(self.targetModeCombo)

        self.fileTopSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.fileTopRow.addItem(self.fileTopSpacer)

        self.filePathLabel = QLabel(self.fileGroup)
        self.filePathLabel.setObjectName(u"filePathLabel")

        self.fileTopRow.addWidget(self.filePathLabel)


        self.fileLayout.addLayout(self.fileTopRow)

        self.fileBottomRow = QHBoxLayout()
        self.fileBottomRow.setObjectName(u"fileBottomRow")
        self.fileAx1Label = QLabel(self.fileGroup)
        self.fileAx1Label.setObjectName(u"fileAx1Label")

        self.fileBottomRow.addWidget(self.fileAx1Label)

        self.fileTarget1Spin = QDoubleSpinBox(self.fileGroup)
        self.fileTarget1Spin.setObjectName(u"fileTarget1Spin")

        self.fileBottomRow.addWidget(self.fileTarget1Spin)

        self.fileAx2Label = QLabel(self.fileGroup)
        self.fileAx2Label.setObjectName(u"fileAx2Label")

        self.fileBottomRow.addWidget(self.fileAx2Label)

        self.fileTarget2Spin = QDoubleSpinBox(self.fileGroup)
        self.fileTarget2Spin.setObjectName(u"fileTarget2Spin")

        self.fileBottomRow.addWidget(self.fileTarget2Spin)

        self.fileAx3Label = QLabel(self.fileGroup)
        self.fileAx3Label.setObjectName(u"fileAx3Label")

        self.fileBottomRow.addWidget(self.fileAx3Label)

        self.fileTarget3Spin = QDoubleSpinBox(self.fileGroup)
        self.fileTarget3Spin.setObjectName(u"fileTarget3Spin")

        self.fileBottomRow.addWidget(self.fileTarget3Spin)

        self.fileSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.fileBottomRow.addItem(self.fileSpacer)

        self.fileCopyButton = QPushButton(self.fileGroup)
        self.fileCopyButton.setObjectName(u"fileCopyButton")

        self.fileBottomRow.addWidget(self.fileCopyButton)

        self.fileSaveButton = QPushButton(self.fileGroup)
        self.fileSaveButton.setObjectName(u"fileSaveButton")

        self.fileBottomRow.addWidget(self.fileSaveButton)

        self.fileMoveButton = QPushButton(self.fileGroup)
        self.fileMoveButton.setObjectName(u"fileMoveButton")

        self.fileBottomRow.addWidget(self.fileMoveButton)


        self.fileLayout.addLayout(self.fileBottomRow)


        self.rootLayout.addWidget(self.fileGroup)

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
        self.triggerButton.setText(QCoreApplication.translate("MainWindow", u"\u30c8\u30ea\u30ac\u51fa\u529b\u2026", None))
        self.statusGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u72b6\u614b", None))
        self.stateLabel.setText(QCoreApplication.translate("MainWindow", u"\u672a\u63a5\u7d9a", None))
        self.interlockLabel.setText(QCoreApplication.translate("MainWindow", u"\u30a4\u30f3\u30bf\u30fc\u30ed\u30c3\u30af: -", None))
        self.limitLabel.setText(QCoreApplication.translate("MainWindow", u"\u30ea\u30df\u30c3\u30c8: -", None))
        self.stopAllButton.setText(QCoreApplication.translate("MainWindow", u"\u5168\u8ef8\u5373\u505c\u6b62", None))
        self.stageGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u30b9\u30c6\u30fc\u30b8\u64cd\u4f5c", None))
        self.jogSpeedLabel.setText(QCoreApplication.translate("MainWindow", u"\u30b8\u30e7\u30b0\u901f\u5ea6\uff08\u5168\u8ef8\u5171\u901a\uff09", None))
        self.fileGroup.setTitle(QCoreApplication.translate("MainWindow", u"3\u8ef8\u540c\u6642\u79fb\u52d5\uff08\u76ee\u6a19\u4f4d\u7f6e\u30e9\u30a4\u30d6\u30e9\u30ea\uff09", None))
        self.targetSelLabel.setText(QCoreApplication.translate("MainWindow", u"\u76ee\u6a19\uff08\u756a\u53f7\uff1a\u540d\u524d\uff09", None))
        self.targetModeLabel.setText(QCoreApplication.translate("MainWindow", u"\u30e2\u30fc\u30c9", None))
        self.filePathLabel.setText(QCoreApplication.translate("MainWindow", u"\uff08\u672a\u8aad\u8fbc\uff09", None))
        self.fileAx1Label.setText(QCoreApplication.translate("MainWindow", u"\u8ef81", None))
        self.fileAx2Label.setText(QCoreApplication.translate("MainWindow", u"\u8ef82", None))
        self.fileAx3Label.setText(QCoreApplication.translate("MainWindow", u"\u8ef83", None))
        self.fileCopyButton.setText(QCoreApplication.translate("MainWindow", u"\u73fe\u5728\u4f4d\u7f6e\u3092\u30b3\u30d4\u30fc", None))
        self.fileSaveButton.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58\uff08\u4e0a\u66f8\u304d\uff09", None))
        self.fileMoveButton.setText(QCoreApplication.translate("MainWindow", u"3\u8ef8\u7d76\u5bfe\u79fb\u52d5", None))
        self.commandGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u76f4\u63a5\u30b3\u30de\u30f3\u30c9", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"\u9001\u4fe1", None))
        self.logGroup.setTitle(QCoreApplication.translate("MainWindow", u"\u30ed\u30b0", None))
    # retranslateUi

