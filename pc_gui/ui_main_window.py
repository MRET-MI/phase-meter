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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QVBoxLayout, QWidget)

from plot_widget import RollingPlot

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1300, 780)
        self.rootLayout = QHBoxLayout(MainWindow)
        self.rootLayout.setObjectName(u"rootLayout")
        self.leftLayout = QVBoxLayout()
        self.leftLayout.setObjectName(u"leftLayout")
        self.connLayout = QHBoxLayout()
        self.connLayout.setObjectName(u"connLayout")
        self.portLabel = QLabel(MainWindow)
        self.portLabel.setObjectName(u"portLabel")

        self.connLayout.addWidget(self.portLabel)

        self.portCombo = QComboBox(MainWindow)
        self.portCombo.setObjectName(u"portCombo")
        self.portCombo.setMinimumWidth(240)

        self.connLayout.addWidget(self.portCombo)

        self.refreshButton = QPushButton(MainWindow)
        self.refreshButton.setObjectName(u"refreshButton")

        self.connLayout.addWidget(self.refreshButton)

        self.connectButton = QPushButton(MainWindow)
        self.connectButton.setObjectName(u"connectButton")

        self.connLayout.addWidget(self.connectButton)


        self.leftLayout.addLayout(self.connLayout)

        self.stageGroup = QGroupBox(MainWindow)
        self.stageGroup.setObjectName(u"stageGroup")
        self.stageConnLayout = QHBoxLayout(self.stageGroup)
        self.stageConnLayout.setObjectName(u"stageConnLayout")
        self.stagePortLabel = QLabel(self.stageGroup)
        self.stagePortLabel.setObjectName(u"stagePortLabel")

        self.stageConnLayout.addWidget(self.stagePortLabel)

        self.stagePortCombo = QComboBox(self.stageGroup)
        self.stagePortCombo.setObjectName(u"stagePortCombo")
        self.stagePortCombo.setMinimumWidth(200)

        self.stageConnLayout.addWidget(self.stagePortCombo)

        self.stageRefreshButton = QPushButton(self.stageGroup)
        self.stageRefreshButton.setObjectName(u"stageRefreshButton")

        self.stageConnLayout.addWidget(self.stageRefreshButton)

        self.stageConnectButton = QPushButton(self.stageGroup)
        self.stageConnectButton.setObjectName(u"stageConnectButton")

        self.stageConnLayout.addWidget(self.stageConnectButton)

        self.openStageGuiButton = QPushButton(self.stageGroup)
        self.openStageGuiButton.setObjectName(u"openStageGuiButton")

        self.stageConnLayout.addWidget(self.openStageGuiButton)

        self.stageStatusLabel = QLabel(self.stageGroup)
        self.stageStatusLabel.setObjectName(u"stageStatusLabel")
        self.stageStatusLabel.setStyleSheet(u"color: #555;")

        self.stageConnLayout.addWidget(self.stageStatusLabel)


        self.leftLayout.addWidget(self.stageGroup)

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

        self.settingsButton = QPushButton(MainWindow)
        self.settingsButton.setObjectName(u"settingsButton")

        self.ctrlLayout.addWidget(self.settingsButton)

        self.ctrlSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.ctrlLayout.addItem(self.ctrlSpacer)


        self.leftLayout.addLayout(self.ctrlLayout)

        self.acqGroup = QGroupBox(MainWindow)
        self.acqGroup.setObjectName(u"acqGroup")
        self.acqLayout = QHBoxLayout(self.acqGroup)
        self.acqLayout.setObjectName(u"acqLayout")
        self.modeCombo = QComboBox(self.acqGroup)
        self.modeCombo.setObjectName(u"modeCombo")

        self.acqLayout.addWidget(self.modeCombo)

        self.durationLabel = QLabel(self.acqGroup)
        self.durationLabel.setObjectName(u"durationLabel")

        self.acqLayout.addWidget(self.durationLabel)

        self.durationSpin = QDoubleSpinBox(self.acqGroup)
        self.durationSpin.setObjectName(u"durationSpin")
        self.durationSpin.setDecimals(1)
        self.durationSpin.setMinimum(0.100000000000000)
        self.durationSpin.setMaximum(3600.000000000000000)
        self.durationSpin.setSingleStep(1.000000000000000)
        self.durationSpin.setValue(10.000000000000000)

        self.acqLayout.addWidget(self.durationSpin)

        self.countLabel = QLabel(self.acqGroup)
        self.countLabel.setObjectName(u"countLabel")

        self.acqLayout.addWidget(self.countLabel)

        self.countSpin = QSpinBox(self.acqGroup)
        self.countSpin.setObjectName(u"countSpin")
        self.countSpin.setMinimum(1)
        self.countSpin.setMaximum(10000000)
        self.countSpin.setSingleStep(100)
        self.countSpin.setValue(1000)
        self.countSpin.setGroupSeparatorShown(True)

        self.acqLayout.addWidget(self.countSpin)


        self.leftLayout.addWidget(self.acqGroup)

        self.attenDacRow = QHBoxLayout()
        self.attenDacRow.setObjectName(u"attenDacRow")
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


        self.attenDacRow.addWidget(self.attenGroup)

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


        self.attenDacRow.addWidget(self.dacGroup)


        self.leftLayout.addLayout(self.attenDacRow)

        self.potGroup = QGroupBox(MainWindow)
        self.potGroup.setObjectName(u"potGroup")
        self.potLayout = QHBoxLayout(self.potGroup)
        self.potLayout.setObjectName(u"potLayout")
        self.potTxLabel = QLabel(self.potGroup)
        self.potTxLabel.setObjectName(u"potTxLabel")

        self.potLayout.addWidget(self.potTxLabel)

        self.potTxSpin = QSpinBox(self.potGroup)
        self.potTxSpin.setObjectName(u"potTxSpin")
        self.potTxSpin.setMaximum(256)
        self.potTxSpin.setValue(128)

        self.potLayout.addWidget(self.potTxSpin)

        self.potTxSetButton = QPushButton(self.potGroup)
        self.potTxSetButton.setObjectName(u"potTxSetButton")

        self.potLayout.addWidget(self.potTxSetButton)

        self.potRxLabel = QLabel(self.potGroup)
        self.potRxLabel.setObjectName(u"potRxLabel")

        self.potLayout.addWidget(self.potRxLabel)

        self.potRxSpin = QSpinBox(self.potGroup)
        self.potRxSpin.setObjectName(u"potRxSpin")
        self.potRxSpin.setMaximum(256)
        self.potRxSpin.setValue(128)

        self.potLayout.addWidget(self.potRxSpin)

        self.potRxSetButton = QPushButton(self.potGroup)
        self.potRxSetButton.setObjectName(u"potRxSetButton")

        self.potLayout.addWidget(self.potRxSetButton)


        self.leftLayout.addWidget(self.potGroup)

        self.valueFreqLayout = QHBoxLayout()
        self.valueFreqLayout.setObjectName(u"valueFreqLayout")
        self.valueLabel = QLabel(MainWindow)
        self.valueLabel.setObjectName(u"valueLabel")
        self.valueLabel.setStyleSheet(u"font-size: 16px; font-weight: 600;")

        self.valueFreqLayout.addWidget(self.valueLabel)

        self.freqLabel = QLabel(MainWindow)
        self.freqLabel.setObjectName(u"freqLabel")
        self.freqLabel.setStyleSheet(u"font-size: 16px; color: #555;")

        self.valueFreqLayout.addWidget(self.freqLabel)

        self.valueFreqSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.valueFreqLayout.addItem(self.valueFreqSpacer)


        self.leftLayout.addLayout(self.valueFreqLayout)

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


        self.leftLayout.addLayout(self.cmdLayout)

        self.autoGroup = QGroupBox(MainWindow)
        self.autoGroup.setObjectName(u"autoGroup")
        self.autoLayout = QHBoxLayout(self.autoGroup)
        self.autoLayout.setObjectName(u"autoLayout")
        self.loadScriptButton = QPushButton(self.autoGroup)
        self.loadScriptButton.setObjectName(u"loadScriptButton")

        self.autoLayout.addWidget(self.loadScriptButton)

        self.runScriptButton = QPushButton(self.autoGroup)
        self.runScriptButton.setObjectName(u"runScriptButton")

        self.autoLayout.addWidget(self.runScriptButton)

        self.stopScriptButton = QPushButton(self.autoGroup)
        self.stopScriptButton.setObjectName(u"stopScriptButton")

        self.autoLayout.addWidget(self.stopScriptButton)

        self.scriptLabel = QLabel(self.autoGroup)
        self.scriptLabel.setObjectName(u"scriptLabel")
        self.scriptLabel.setStyleSheet(u"color: #555;")

        self.autoLayout.addWidget(self.scriptLabel)


        self.leftLayout.addWidget(self.autoGroup)

        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.setObjectName(u"bottomLayout")
        self.logEdit = QPlainTextEdit(MainWindow)
        self.logEdit.setObjectName(u"logEdit")
        self.logEdit.setMaximumBlockCount(500)
        self.logEdit.setReadOnly(True)
        self.logEdit.setMinimumHeight(120)
        self.logEdit.setMaximumWidth(420)

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

        self.bottomButtonsSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.bottomButtons.addItem(self.bottomButtonsSpacer)


        self.bottomLayout.addLayout(self.bottomButtons)


        self.leftLayout.addLayout(self.bottomLayout)


        self.rootLayout.addLayout(self.leftLayout)

        self.rightLayout = QVBoxLayout()
        self.rightLayout.setObjectName(u"rightLayout")
        self.phasePlot = RollingPlot(MainWindow)
        self.phasePlot.setObjectName(u"phasePlot")
        self.phasePlot.setMinimumWidth(420)
        self.phasePlot.setMinimumHeight(180)

        self.rightLayout.addWidget(self.phasePlot)

        self.ampPlot = RollingPlot(MainWindow)
        self.ampPlot.setObjectName(u"ampPlot")
        self.ampPlot.setMinimumWidth(420)
        self.ampPlot.setMinimumHeight(180)

        self.rightLayout.addWidget(self.ampPlot)

        self.tempPlot = RollingPlot(MainWindow)
        self.tempPlot.setObjectName(u"tempPlot")
        self.tempPlot.setMinimumWidth(420)
        self.tempPlot.setMinimumHeight(180)

        self.rightLayout.addWidget(self.tempPlot)


        self.rootLayout.addLayout(self.rightLayout)


        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Phase Meter \u2014 2ch phase difference", None))
        self.portLabel.setText(QCoreApplication.translate("MainWindow", u"Port:", None))
        self.refreshButton.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.connectButton.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.stageGroup.setTitle(QCoreApplication.translate("MainWindow", u"Stage (CP-700M)", None))
        self.stagePortLabel.setText(QCoreApplication.translate("MainWindow", u"Port:", None))
        self.stageRefreshButton.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.stageConnectButton.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.openStageGuiButton.setText(QCoreApplication.translate("MainWindow", u"Open control GUI\u2026", None))
        self.stageStatusLabel.setText(QCoreApplication.translate("MainWindow", u"(stage not connected)", None))
        self.runButton.setText(QCoreApplication.translate("MainWindow", u"RUN", None))
        self.stopButton.setText(QCoreApplication.translate("MainWindow", u"STOP", None))
        self.verButton.setText(QCoreApplication.translate("MainWindow", u"VER", None))
        self.settingsButton.setText(QCoreApplication.translate("MainWindow", u"Settings\u2026", None))
        self.acqGroup.setTitle(QCoreApplication.translate("MainWindow", u"Acquisition", None))
        self.durationLabel.setText(QCoreApplication.translate("MainWindow", u"duration", None))
        self.durationSpin.setSuffix(QCoreApplication.translate("MainWindow", u" s", None))
        self.countLabel.setText(QCoreApplication.translate("MainWindow", u"count", None))
        self.countSpin.setSuffix(QCoreApplication.translate("MainWindow", u" pts", None))
        self.attenGroup.setTitle(QCoreApplication.translate("MainWindow", u"Attenuator [dB]", None))
        self.txLabel.setText(QCoreApplication.translate("MainWindow", u"TX", None))
        self.txSetButton.setText(QCoreApplication.translate("MainWindow", u"Set TX", None))
        self.rxLabel.setText(QCoreApplication.translate("MainWindow", u"RX", None))
        self.rxSetButton.setText(QCoreApplication.translate("MainWindow", u"Set RX", None))
        self.dacGroup.setTitle(QCoreApplication.translate("MainWindow", u"DAC PA5 [V]", None))
        self.dacSetButton.setText(QCoreApplication.translate("MainWindow", u"Set DAC", None))
        self.potGroup.setTitle(QCoreApplication.translate("MainWindow", u"Pot MCP41HV51 [0-256]", None))
        self.potTxLabel.setText(QCoreApplication.translate("MainWindow", u"TX", None))
        self.potTxSetButton.setText(QCoreApplication.translate("MainWindow", u"Set TX", None))
        self.potRxLabel.setText(QCoreApplication.translate("MainWindow", u"RX", None))
        self.potRxSetButton.setText(QCoreApplication.translate("MainWindow", u"Set RX", None))
        self.valueLabel.setText(QCoreApplication.translate("MainWindow", u"phase: \u2014", None))
        self.freqLabel.setText(QCoreApplication.translate("MainWindow", u"peak freq: \u2014    amp: \u2014", None))
        self.cmdLabel.setText(QCoreApplication.translate("MainWindow", u"Cmd:", None))
        self.cmdEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"send command (e.g. DBG, R1R) \u2014 Enter to send", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"Send", None))
        self.autoGroup.setTitle(QCoreApplication.translate("MainWindow", u"Auto measure (script)", None))
        self.loadScriptButton.setText(QCoreApplication.translate("MainWindow", u"Load script\u2026", None))
        self.runScriptButton.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.stopScriptButton.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.scriptLabel.setText(QCoreApplication.translate("MainWindow", u"(no script)", None))
        self.saveDataButton.setText(QCoreApplication.translate("MainWindow", u"Save all data\u2026", None))
        self.csvButton.setText(QCoreApplication.translate("MainWindow", u"Start CSV log\u2026", None))
        self.clearButton.setText(QCoreApplication.translate("MainWindow", u"Clear data", None))
    # retranslateUi

