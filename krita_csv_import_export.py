from krita import *
from .csv_exporter import exportCSV, displayCSVExportPrompt
from PyQt5.QtWidgets import QMessageBox, QFileDialog

def startCSVExport():
    document = Application.activeDocument()
    if document == None:
        QMessageBox.information(Application.activeWindow().qwindow(), "Export failed", "No file is currently open.")
        return
    
    displayCSVExportPrompt()

class CSVImportExport(Extension):

    def __init__(self, parent):
        #This is initialising the parent, always  important when subclassing.
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        exportAction = window.createAction("export_csv_plugin", "Export animation to CSV", "tools")
        exportAction.triggered.connect(startCSVExport)

# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(CSVImportExport(Krita.instance()))
