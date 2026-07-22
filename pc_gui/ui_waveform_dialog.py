# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'waveform_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

from plot_widget import WaveformPlot

class Ui_WaveformDialog(object):
    def setupUi(self, WaveformDialog):
        if not WaveformDialog.objectName():
            WaveformDialog.setObjectName(u"WaveformDialog")
        WaveformDialog.resize(820, 520)
        self.waveRootLayout = QVBoxLayout(WaveformDialog)
        self.waveRootLayout.setObjectName(u"waveRootLayout")
        self.waveCtrlLayout = QHBoxLayout()
        self.waveCtrlLayout.setObjectName(u"waveCtrlLayout")
        self.captureButton = QPushButton(WaveformDialog)
        self.captureButton.setObjectName(u"captureButton")

        self.waveCtrlLayout.addWidget(self.captureButton)

        self.liveCheck = QCheckBox(WaveformDialog)
        self.liveCheck.setObjectName(u"liveCheck")

        self.waveCtrlLayout.addWidget(self.liveCheck)

        self.liveRateSpin = QDoubleSpinBox(WaveformDialog)
        self.liveRateSpin.setObjectName(u"liveRateSpin")
        self.liveRateSpin.setDecimals(1)
        self.liveRateSpin.setMinimum(0.500000000000000)
        self.liveRateSpin.setMaximum(20.000000000000000)
        self.liveRateSpin.setSingleStep(1.000000000000000)
        self.liveRateSpin.setValue(3.000000000000000)

        self.waveCtrlLayout.addWidget(self.liveRateSpin)

        self.unitLabel = QLabel(WaveformDialog)
        self.unitLabel.setObjectName(u"unitLabel")

        self.waveCtrlLayout.addWidget(self.unitLabel)

        self.unitCombo = QComboBox(WaveformDialog)
        self.unitCombo.setObjectName(u"unitCombo")

        self.waveCtrlLayout.addWidget(self.unitCombo)

        self.waveCtrlSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.waveCtrlLayout.addItem(self.waveCtrlSpacer)

        self.saveWaveButton = QPushButton(WaveformDialog)
        self.saveWaveButton.setObjectName(u"saveWaveButton")

        self.waveCtrlLayout.addWidget(self.saveWaveButton)

        self.waveInfoLabel = QLabel(WaveformDialog)
        self.waveInfoLabel.setObjectName(u"waveInfoLabel")
        self.waveInfoLabel.setStyleSheet(u"color: #555;")

        self.waveCtrlLayout.addWidget(self.waveInfoLabel)


        self.waveRootLayout.addLayout(self.waveCtrlLayout)

        self.wavePlot = WaveformPlot(WaveformDialog)
        self.wavePlot.setObjectName(u"wavePlot")
        self.wavePlot.setMinimumHeight(380)

        self.waveRootLayout.addWidget(self.wavePlot)


        self.retranslateUi(WaveformDialog)

        QMetaObject.connectSlotsByName(WaveformDialog)
    # setupUi

    def retranslateUi(self, WaveformDialog):
        WaveformDialog.setWindowTitle(QCoreApplication.translate("WaveformDialog", u"Raw waveform \u2014 2ch", None))
        self.captureButton.setText(QCoreApplication.translate("WaveformDialog", u"Capture", None))
        self.liveCheck.setText(QCoreApplication.translate("WaveformDialog", u"Live", None))
        self.liveRateSpin.setSuffix(QCoreApplication.translate("WaveformDialog", u" Hz", None))
        self.unitLabel.setText(QCoreApplication.translate("WaveformDialog", u"Unit:", None))
        self.saveWaveButton.setText(QCoreApplication.translate("WaveformDialog", u"Save\u2026", None))
        self.waveInfoLabel.setText(QCoreApplication.translate("WaveformDialog", u"(no capture)", None))
    # retranslateUi

