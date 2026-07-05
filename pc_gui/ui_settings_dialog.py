# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QVBoxLayout, QWidget)

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        if not SettingsDialog.objectName():
            SettingsDialog.setObjectName(u"SettingsDialog")
        SettingsDialog.resize(560, 200)
        self.dlgRootLayout = QVBoxLayout(SettingsDialog)
        self.dlgRootLayout.setObjectName(u"dlgRootLayout")
        self.settingsGroup = QGroupBox(SettingsDialog)
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


        self.dlgRootLayout.addWidget(self.settingsGroup)

        self.dlgSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dlgRootLayout.addItem(self.dlgSpacer)


        self.retranslateUi(SettingsDialog)

        QMetaObject.connectSlotsByName(SettingsDialog)
    # setupUi

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QCoreApplication.translate("SettingsDialog", u"Settings \u2014 phase calc", None))
        self.settingsGroup.setTitle(QCoreApplication.translate("SettingsDialog", u"Settings (phase calc)", None))
        self.adcNumLabel.setText(QCoreApplication.translate("SettingsDialog", u"adc_num", None))
        self.fsLabel.setText(QCoreApplication.translate("SettingsDialog", u"fs", None))
        self.fsSpin.setSuffix(QCoreApplication.translate("SettingsDialog", u" Hz", None))
        self.targetLabel.setText(QCoreApplication.translate("SettingsDialog", u"target", None))
        self.targetSpin.setSuffix(QCoreApplication.translate("SettingsDialog", u" Hz", None))
        self.readButton.setText(QCoreApplication.translate("SettingsDialog", u"Read", None))
        self.peakLabel.setText(QCoreApplication.translate("SettingsDialog", u"peak", None))
        self.searchWinLabel.setText(QCoreApplication.translate("SettingsDialog", u"search_win", None))
        self.bandWLabel.setText(QCoreApplication.translate("SettingsDialog", u"band_w", None))
        self.applyButton.setText(QCoreApplication.translate("SettingsDialog", u"Apply", None))
        self.maxOffsetLabel.setText(QCoreApplication.translate("SettingsDialog", u"maxoffset", None))
        self.saveFlashButton.setText(QCoreApplication.translate("SettingsDialog", u"Save\u2192Flash", None))
    # retranslateUi

