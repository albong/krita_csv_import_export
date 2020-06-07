# Copyright Alex Bongiovanni 2020
#
#

from krita import *
from PyQt5.QtWidgets import QWidget, QMessageBox
import os
import os.path
import shutil


#we run in batch mode, force max quality PNG's
PNG_CONFIG = InfoObject()
PNG_CONFIG.setProperty("alpha", True)
PNG_CONFIG.setProperty("interlaced", False)
PNG_CONFIG.setProperty("compression", 1)
PNG_CONFIG.setProperty("indexed", False)
PNG_CONFIG.setProperty("saveSRGBProfile", False)
PNG_CONFIG.setProperty("forceSRGB", True)
PNG_CONFIG.setProperty("storeMetadata", False)
PNG_CONFIG.setProperty("storeAuthor", False)

#################################################
# Constants
#################################################

#convert Krita blend modes to TVPaint modes
BLEND_MODES = {
    "normal" : "Color",
    "multiply" : "Multiply",
    #"???" : "Screen",
    "overlay" : "Overlay",
    "addition" : "Add",
    "erase" : "Difference",
    "saturation" : "Saturation",
    "luminosity" : "Value"
}


#################################################
# Methods
#################################################

def writeCSVLine(fout, tokenList):
    """This writes out a csv line. It appears that the format uses ', ' as a delimiter instead of just ',', and python's builtin csv library doesn't support multichar delimiters."""
    escapedTokens = []
    for i in range(0, len(tokenList)):
        try:
            if ',' in tokenList[i]:
                escapedTokens.append('"' + tokenList[i] + '"')
            else:
                escapedTokens.append(tokenList[i])
        except TypeError as e:
            print(tokenList)
            raise e
    
    fout.write(", ".join(escapedTokens) + "\r\n") #end with \r\n

def flattenNodesToList(root):
    """Walks the tree of nodes (layers) and puts them into a list in visibility order, ignoring groups of layers. Not actually sure how layer groups work with animation."""
    result = []
    
    for child in root.childNodes():
        result += flattenNodesToList(child)
        
    if root.type() != "grouplayer":
        result += [root]
        
    return result


#################################################
# Script start
#################################################

def main():
    activeDocument = Krita.instance().activeDocument()
    batchModeOriginalState = Krita.instance().batchmode()
    Krita.instance().setBatchmode(True)
    originalTime = activeDocument.currentTime()
    
    #retrieve the basic data
    fullFilePath = os.path.splitext(activeDocument.fileName())[0]
    projectName = os.path.split(fullFilePath)[1]
    width = activeDocument.width()
    height = activeDocument.height()
    animationStartTime = activeDocument.fullClipRangeStartTime()
    animationEndTime = activeDocument.fullClipRangeEndTime()
    frameCount = animationEndTime - animationStartTime + 1
    frameRate = activeDocument.framesPerSecond()
    resolutionPPP = float(activeDocument.resolution()) / 72.0 #72 pts per inch, convert from pixels per inch
    documentQRect = QRect(0, 0, width, height)
    
    #check for existing files, ask use if they want to remove
    csvFilename = fullFilePath + ".csv"
    framesDirectory = fullFilePath + ".frames"
    if os.path.isdir(framesDirectory) or os.path.isfile(csvFilename):
        confirmDelete = QMessageBox.question(Application.activeWindow().qwindow(), "Files already exist", "CSV export files with the name '" + fullFilePath + "' already exist. Do you want to remove these? This cannot be undone.")
        if confirmDelete == QMessageBox.Yes:
            shutil.rmtree(framesDirectory)
        else:
            QMessageBox.information(Application.activeWindow().qwindow(), "Export failed", "CSV export cancelled.")
            return
    try:
        os.mkdir(framesDirectory)
    except OSError as e:
        QMessageBox.information(Application.activeWindow().qwindow(), "Export failed", "Error creating output directory: " + str(e))
        return
    
    #get all the non-group layers in a list, we don't care about the layer hierarchy
    layerNodes = flattenNodesToList(activeDocument.rootNode())
    layerNodes.reverse() #by default are bottom to top, but we want to reverse that
    layerCount = len(layerNodes)
    
    #used below for saving so we don't need to pass around the directory and resolution and rectangle
    def filenameFromLayerAndFrame(layerNumber, frameNumber):
        filenamePrefix = ("0000" + str(layerNumber + 1))[-5:]
        frameNumberString = ("0000" + str(frameNumber))[-5:]
        return os.path.join(framesDirectory, "frame" + filenamePrefix + "-" + frameNumberString + ".png")
    
    
    #loop over and save off all layers regardless of visibility, at each possible frame
    layerFrameLists = []
    for i in range(0, len(layerNodes)):
        layerProcessing = layerNodes[i]
        layerFrames = []
        
        #since we need to save the filenames in the csv file, we generate that and compare against the filename for the last frame
        #since the filename will change at keyframes, that tells us whether or not we need to save
        #finally, the filenames are put in a list so that we can write them out to the csv
        previousFilename = ""
        for j in range(animationStartTime, animationEndTime+1):
            filename = previousFilename
            if layerProcessing.animated() == False:
                filename = filenameFromLayerAndFrame(i, 0)
            elif layerProcessing.hasKeyframeAtTime(j):
                activeDocument.setCurrentTime(j)
                filename = filenameFromLayerAndFrame(i, j)
            
            if filename != previousFilename:
                layerProcessing.save(filename, resolutionPPP, resolutionPPP, PNG_CONFIG, documentQRect)
                previousFilename = filename
            
            layerFrames.append(os.path.split(filename)[1])
            
        layerFrameLists.append(layerFrames)
    
    #now we can save out the csv
    with open(csvFilename, "w") as fout:
        #headers - don't know what "Pixel Aspect Ratio" and "Field Mode" are
        writeCSVLine(fout, ["UTF-8", "TVPaint", "CSV 1.0"])
        writeCSVLine(fout, ["Project Name", "Width", "Height", "Frame Count", "Layer Count", "Frame Rate", "Pixel Aspect Ratio", "Field Mode"])
        writeCSVLine(fout, [projectName, str(width), str(height), str(frameCount), str(layerCount), str(float(frameRate)), str(1.0), "Progressive"])
        
        #layer info
        layerNames = ["#Layers"]
        layerDensity = ["#Density"] #I assume this is resolution?
        layerBlending = ["#Blending"]
        layerVisible = ["#Visible"]
        for i in range(0, len(layerNodes)):
            currNode = layerNodes[i]
            layerNames.append(currNode.name())
            layerDensity.append(str(float(currNode.opacity()) / 255))
            if currNode.blendingMode() in BLEND_MODES:
                layerBlending.append(BLEND_MODES[currNode.blendingMode()])
            else:
                layerBlending.append("ERROR")
            if currNode.visible():
                layerVisible.append("1")
            else:
                layerVisible.append("0")
        writeCSVLine(fout, layerNames)
        writeCSVLine(fout, layerDensity)
        writeCSVLine(fout, layerBlending)
        writeCSVLine(fout, layerVisible)
        
        #write frame data
        for j in range(animationStartTime, animationEndTime + 1):
            firstColumn = "#" + ("0000" + str(j))[-5:]
            line = [firstColumn]
            for i in range(0, len(layerFrameLists)):
                line.append(layerFrameLists[i][j])
            writeCSVLine(fout, line)
    
    #reset batch mode (is this necessary?) and alert the user we're finished
    Krita.instance().setBatchmode(batchModeOriginalState)
    activeDocument.setCurrentTime(originalTime)
    print("Done!")

#Krita automagically runs the main function
#if __name__ == "__main__":
#    main()

"""
Still to be done:

quote the names of things

add progress bar and run this in a separate thread

folder support?

figure out how layer groups get animated

license (how work with krita?) and copyright

package it for distribution?
"""
