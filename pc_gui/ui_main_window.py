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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

from plot_widget import RollingPlot

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(960, 720)
        self.rootLayout = QVBoxLayout(MainWindow)
        self.rootLayout.setObjectName(u"rootLayout")
        self.connLayout = QHBoxLayout()
        self.connLayout.setObjectName(u"connLayout")
        self.portLabel = QLabel(MainWindow)
        self.portLabel.setObjectName(u"portLabel")

        self.connLayout.addWidget(self.portLabel)

        self.portCombo = QComboBox(MainWindow)
        self.portCombo.setObjectName(u"portCombo")
        self.portCombo.setMinimumWidth(280)

        self.connLayout.addWidget(self.portCombo)

        self.refreshButton = QPushButton(MainWindow)
        self.refreshButton.setObjectName(u"refreshButton")

        self.connLayout.addWidget(self.refreshButton)

        self.connectButton = QPushButton(MainWindow)
        self.connectButton.setObjectName(u"connectButton")

        self.connLayout.addWidget(self.connectButton)


        self.rootLayout.addLayout(self.connLayout)

        self.ctrlLayout = QHBoxLayout()
        self.ctrlLayout.setObjectName(u"ctrlLayout")
        self.runButton = QPushButton(MainWindow)
        self.runButton.setObjectName(u"runButton")

        self.ctrlLayout.addWidget(self.runButton)

        self.stopButton = QPushButton(MainWindow)
        self.stopButton.setObjectName(u"stopButton")

        self.ctrlLayout.addWidget(self.stopButton)

        self.verButton = QPushButton(MainWindow)
        self.verButton.setObjectName(u"verButton")

        self.ctrlLayout.addWidget(self.verButton)

        self.ctrlSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.ctrlLayout.addItem(self.ctrlSpacer)

        self.attenGroup = QGroupBox(MainWindow)
        self.attenGroup.setObjectName(u"attenGroup")
        self.attenLayout = QHBoxLayout(self.attenGroup)
        self.attenLayout.setObjectName(u"attenLayout")
        self.txLabel = QLabel(self.attenGroup)
        self.txLabel.setObjectName(u"txLabel")

        self.attenLayout.addWidget(self.txLabel)

        self.txSpin = QDoubleSpinBox(self.attenGroup)
        self.txSpin.setObjectName(u"txSpin")
        self.txSpin.setDecimals(1)
        self.txSpin.setMaximum(31.500000000000000)
        self.txSpin.setSingleStep(0.500000000000000)

        self.attenLayout.addWidget(self.txSpin)

        self.txSetButton = QPushButton(self.attenGroup)
        self.txSetButton.setObjectName(u"txSetButton")

        self.attenLayout.addWidget(self.txSetButton)

        self.rxLabel = QLabel(self.attenGroup)
        self.rxLabel.setObjectName(u"rxLabel")

        self.attenLayout.addWidget(self.rxLabel)

        self.rxSpin = QDoubleSpinBox(self.attenGroup)
        self.rxSpin.setObjectName(u"rxSpin")
        self.rxSpin.setDecimals(1)
        self.rxSpin.setMaximum(31.500000000000000)
        self.rxSpin.setSingleStep(0.500000000000000)

        self.attenLayout.addWidget(self.rxSpin)

        self.rxSetButton = QPushButton(self.attenGroup)
        self.rxSetButton.setObjectName(u"rxSetButton")

        self.attenLayout.addWidget(self.rxSetButton)


        self.ctrlLayout.addWidget(self.attenGroup)

        self.dacGroup = QGroupBox(MainWindow)
        self.dacGroup.setObjectName(u"dacGroup")
        self.dacLayout = QHBoxLayout(self.dacGroup)
        self.dacLayout.setObjectName(u"dacLayout")
        self.dacSpin = QDoubleSpinBox(self.dacGroup)
        self.dacSpin.setObjectName(u"dacSpin")
        self.dacSpin.setDecimals(3)
        self.dacSpin.setMaximum(3.300000000000000)
        self.dacSpin.setSingleStep(0.010000000000000)
        self.dacSpin.setValue(3.300000000000000)

        self.dacLayout.addWidget(self.dacSpin)

        self.dacSetButton = QPushButton(self.dacGroup)
        self.dacSetButton.setObjectName(u"dacSetButton")

        self.dacLayout.addWidget(self.dacSetButton)


        self.ctrlLayout.addWidget(self.dacGroup)


        self.rootLayout.addLayout(self.ctrlLayout)

        self.settingsGroup = QGroupBox(MainWindow)
        self.settingsGroup.setObjectName(u"settingsGroup")
        self.settingsLayout = QGridLayout(self.settingsGroup)
        self.settingsLayout.setObjectName(u"settingsLayout")
        self.adcNumLabel = QLabel(self.settingsGroup)
        self.adcNumLabel.setObjectName(u"adcNumLabel")

        self.settingsLayout.addWidget(self.adcNumLabel, 0, 0, 1, 1)

        self.adcNumCombo = QComboBox(self.settingsGroup)
        self.adcNumCombo.setObjectName(u"adcNumCombo")

        self.settingsLayout.addWidget(self.adcNumCombo, 0, 1, 1, 1)

        self.fsLabel = QLabel(self.settingsGroup)
        self.fsLabel.setObjectName(u"fsLabel")

        self.settingsLayout.addWidget(self.fsLabel, 0, 2, 1, 1)

        self.fsSpin = QSpinBox(self.settingsGroup)
        self.fsSpin.setObjectName(u"fsSpin")
        self.fsSpin.setMinimum(4000)
        self.fsSpin.setMaximum(2500000)
        self.fsSpin.setSingleStep(1000)
        self.fsSpin.setValue(1000000)

        self.settingsLayout.addWidget(self.fsSpin, 0, 3, 1, 1)

        self.targetLabel = QLabel(self.settingsGroup)
        self.targetLabel.setObjectName(u"targetLabel")

        self.settingsLayout.addWidget(self.targetLabel, 0, 4, 1, 1)

        self.targetSpin = QSpinBox(self.settingsGroup)
        self.targetSpin.setObjectName(u"targetSpin")
        self.targetSpin.setMinimum(1)
        self.targetSpin.setMaximum(1250000)
        self.targetSpin.setValue(100000)

        self.settingsLayout.addWidget(self.targetSpin, 0, 5, 1, 1)

        self.readButton = QPushButton(self.settingsGroup)
        self.readButton.setObjectName(u"readButton")

        self.settingsLayout.addWidget(self.readButton, 0, 6, 1, 1)

        self.peakLabel = QLabel(self.settingsGroup)
        self.peakLabel.setObjectName(u"peakLabel")

        self.settingsLayout.addWidget(self.peakLabel, 1, 0, 1, 1)

        self.peakCombo = QComboBox(self.settingsGroup)
        self.peakCombo.setObjectName(u"peakCombo")

        self.settingsLayout.addWidget(self.peakCombo, 1, 1, 1, 1)

        self.searchWinLabel = QLabel(self.settingsGroup)
        self.searchWinLabel.setObjectName(u"searchWinLabel")

        self.settingsLayout.addWidget(self.searchWinLabel, 1, 2, 1, 1)

        self.searchWinSpin = QSpinBox(self.settingsGroup)
        self.searchWinSpin.setObjectName(u"searchWinSpin")
        self.searchWinSpin.setMaximum(500)
        self.searchWinSpin.setValue(20)

        self.settingsLayout.addWidget(self.searchWinSpin, 1, 3, 1, 1)

        self.bandWLabel = QLabel(self.settingsGroup)
        self.bandWLabel.setObjectName(u"bandWLabel")

        self.settingsLayout.addWidget(self.bandWLabel, 1, 4, 1, 1)

        self.bandWSpin = QSpinBox(self.settingsGroup)
        self.bandWSpin.setObjectName(u"bandWSpin")
        self.bandWSpin.setMaximum(50)
        self.bandWSpin.setValue(2)

        self.settingsLayout.addWidget(self.bandWSpin, 1, 5, 1, 1)

        self.applyButton = QPushButton(self.settingsGroup)
        self.applyButton.setObjectName(u"applyButton")

        self.settingsLayout.addWidget(self.applyButton, 1, 6, 1, 1)

        self.maxOffsetLabel = QLabel(self.settingsGroup)
        self.maxOffsetLabel.setObjectName(u"maxOffsetLabel")

        self.settingsLayout.addWidget(self.maxOffsetLabel, 2, 0, 1, 1)

        self.maxOffsetSpin = QSpinBox(self.settingsGroup)
        self.maxOffsetSpin.setObjectName(u"maxOffsetSpin")
        self.maxOffsetSpin.setMinimum(1)
        self.maxOffsetSpin.setMaximum(500)
        self.maxOffsetSpin.setValue(10)

        self.settingsLayout.addWidget(self.maxOffsetSpin, 2, 1, 1, 1)

        self.saveFlashButton = QPushButton(self.settingsGroup)
        self.saveFlashButton.setObjectName(u"saveFlashButton")

        self.settingsLayout.addWidget(self.saveFlashButton, 2, 6, 1, 1)


        self.rootLayout.addWidget(self.settingsGroup)

        self.cmdLayout = QHBoxLayout()
        self.cmdLayout.setObjectName(u"cmdLayout")
        self.cmdLabel = QLabel(MainWindow)
        self.cmdLabel.setObjectName(u"cmdLabel")

        self.cmdLayout.addWidget(self.cmdLabel)

        self.cmdEdit = QLineEdit(MainWindow)
        self.cmdEdit.setObjectName(u"cmdEdit")

        self.cmdLayout.addWidget(self.cmdEdit)

        self.sendButton = QPushButton(MainWindow)
        self.sendButton.setObjectName(u"sendButton")

        self.cmdLayout.addWidget(self.sendButton)


        self.rootLayout.addLayout(self.cmdLayout)

        self.valueLabel = QLabel(MainWindow)
        self.valueLabel.setObjectName(u"valueLabel")
        self.valueLabel.setStyleSheet(u"font-size: 40px; font-weight: 600;")
        self.valueLabel.setAlignment(Qt.AlignCenter)

        self.rootLayout.addWidget(self.valueLabel)

        self.freqLabel = QLabel(MainWindow)
        self.freqLabel.setObjectName(u"freqLabel")
        self.freqLabel.setStyleSheet(u"font-size: 16px; color: #555;")
        self.freqLabel.setAlignment(Qt.AlignCenter)

        self.rootLayout.addWidget(self.freqLabel)

        self.phasePlot = RollingPlot(MainWindow)
        self.phasePlot.setObjectName(u"phasePlot")
        self.phasePlot.setMinimumHeight(160)

        self.rootLayout.addWidget(self.phasePlot)

        self.ampPlot = RollingPlot(MainWindow)
        self.ampPlot.setObjectName(u"ampPlot")
        self.ampPlot.setMinimumHeight(160)

        self.rootLayout.addWidget(self.ampPlot)

        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.setObjectName(u"bottomLayout")
        self.logEdit = QPlainTextEdit(MainWindow)
        self.logEdit.setObjectName(u"logEdit")
        self.logEdit.setMaximumBlockCount(500)
        self.logEdit.setReadOnly(True)
        self.logEdit.setMaximumHeight(120)

        self.bottomLayout.addWidget(self.logEdit)

        self.bottomButtons = QVBoxLayout()
        self.bottomButtons.setObjectName(u"bottomButtons")
        self.saveDataButton = QPushButton(MainWindow)
        self.saveDataButton.setObjectName(u"saveDataButton")

        self.bottomButtons.addWidget(self.saveDataButton)

        self.csvButton = QPushButton(MainWindow)
        self.csvButton.setObjectName(u"csvButton")

        self.bottomButtons.addWidget(self.csvButton)

        self.clearButton = QPushButton(MainWindow)
        self.clearButton.setObjectName(u"clearButton")

        self.bottomButtons.addWidget(self.clearButton)


        self.bottomLayout.addLayout(self.bottomButtons)


        self.rootLayout.addLayout(self.bottomLayout)


        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Phase Meter \u2014 2ch phase difference", None))
        self.portLabel.setText(QCoreApplication.translate("MainWindow", u"Port:", None))
        self.refreshButton.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.connectButton.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.runButton.setText(QCoreApplication.translate("MainWindow", u"RUN", None))
        self.stopButton.setText(QCoreApplication.translate("MainWindow", u"STOP", None))
        self.verButton.setText(QCoreApplication.translate("MainWindow", u"VER", None))
        self.attenGroup.setTitle(QCoreApplication.translate("MainWindow", u"Attenuator [dB]", None))
        self.txLabel.setText(QCoreApplication.translate("MainWindow", u"TX", None))
        self.txSetButton.setText(QCoreApplication.translate("MainWindow", u"Set TX", None))
        self.rxLabel.setText(QCoreApplication.translate("MainWindow", u"RX", None))
        self.rxSetButton.setText(QCoreApplication.translate("MainWindow", u"Set RX", None))
        self.dacGroup.setTitle(QCoreApplication.translate("MainWindow", u"DAC PA5 [V]", None))
        self.dacSetButton.setText(QCoreApplication.translate("MainWindow", u"Set DAC", None))
        self.settingsGroup.setTitle(QCoreApplication.translate("MainWindow", u"Settings (phase calc)", None))
        self.adcNumLabel.setText(QCoreApplication.translate("MainWindow", u"adc_num", None))
        self.fsLabel.setText(QCoreApplication.translate("MainWindow", u"fs", None))
        self.fsSpin.setSuffix(QCoreApplication.translate("MainWindow", u" Hz", None))
        self.targetLabel.setText(QCoreApplication.translate("MainWindow", u"target", None))
        self.targetSpin.setSuffix(QCoreApplication.translate("MainWindow", u" Hz", None))
        self.readButton.setText(QCoreApplication.translate("MainWindow", u"Read", None))
        self.peakLabel.setText(QCoreApplication.translate("MainWindow", u"peak", None))
        self.searchWinLabel.setText(QCoreApplication.translate("MainWindow", u"search_win", None))
        self.bandWLabel.setText(QCoreApplication.translate("MainWindow", u"band_w", None))
        self.applyButton.setText(QCoreApplication.translate("MainWindow", u"Apply", None))
        self.maxOffsetLabel.setText(QCoreApplication.translate("MainWindow", u"maxoffset", None))
        self.saveFlashButton.setText(QCoreApplication.translate("MainWindow", u"Save\u2192Flash", None))
        self.cmdLabel.setText(QCoreApplication.translate("MainWindow", u"Cmd:", None))
        self.cmdEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"send command (e.g. DBG, R1R) \u2014 Enter to send", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"Send", None))
        self.valueLabel.setText(QCoreApplication.translate("MainWindow", u"\u2014", None))
        self.freqLabel.setText(QCoreApplication.translate("MainWindow", u"peak freq: \u2014    amp: \u2014", None))
        self.saveDataButton.setText(QCoreApplication.translate("MainWindow", u"Save all data\u2026", None))
        self.csvButton.setText(QCoreApplication.translate("MainWindow", u"Start CSV log\u2026", None))
        self.clearButton.setText(QCoreApplication.translate("MainWindow", u"Clear data", None))
    # retranslateUi

