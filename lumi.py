from tkinter import *
from time import time
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import askokcancel, showerror
from tkinter.simpledialog import askstring
from serial import Serial
from tkinter.colorchooser import askcolor
import pickle
import threading

class Polygon:
    def __init__(self, polygon, cmd, offCmd, color="white"):
        self.polygon=polygon
        self.cmd=cmd
        self.offCmd=offCmd
        self.figure=None
        self.color=color
        self.state=False
        self.ghost=True


    def show(self, can):
        if not self.state:
            if self.figure:
                can.itemconfig(self.figure, fill=self.color, outline="white")
            else:
                self.figure=can.create_polygon(*self.polygon, outline="white", fill=self.color)
        self.state=True

    def hide(self, can):
        if self.state:
            if self.ghost:
                can.itemconfig(self.figure, fill="", outline="grey")
            else:
                can.itemconfig(self.figure, fill="", outline="black")
        self.state=False

    def handle(self, cmd, can):
        if self.cmd in cmd:
            self.show(can)
        elif self.offCmd in cmd:
            self.hide(can)


class Lumi:
    def __init__(self):
        "__init__"
        self.tk=Tk()
        self.tk.title("Lumi")
        self.loadDisplayBtn=Button(self.tk, text="Load Display", command=self.loadDisplay)
        self.saveDisplayBtn=Button(self.tk, text="Save Display", command=self.saveDisplay)
        self.loadBtn=Button(self.tk, text="Load synchro", command=self.load)
        self.saveBtn=Button(self.tk, text="Save synchro", command=self.save)
        self.showModeBtn=Button(self.tk, text="Enter show mode", command=self.showMode)
        self.startRecordingBtn = Button(self.tk, text="Start recording", command=lambda: self.tk.bind("<FocusOut>", lambda e:self.startRecording()))
        Button(self.tk, text="Start lightzer", command=lambda: lightzer.init(self)).pack()
        self.ghostifyBtn=Button(self.tk, text="UnGhostify polygons", command=self.ghostify)
        self.ghostifyBtn.pack()
        self.startRecordingBtn.pack()
        self.channelsFrame=Frame(self.tk)
        self.loadDisplayBtn.pack()
        self.saveDisplayBtn.pack()
        self.loadBtn.pack()
        self.saveBtn.pack()
        self.showModeBtn.pack()
        self.channelsFrame.pack()
        self.channels={}
        self.serial=None
        self.previewImgFile=None
        self.previewImg=None
        self.preview={}
        self.prevWin=Toplevel(self.tk)
        self.prevWin.title("Preview - Lumi")
        self.prevCan=Canvas(self.prevWin, height=720, width=1080, background="black")
        self.prevCan.bind("<Button-1>", self.beginPreviewPolygon)
        self.prevCan.pack()
        self.channelsLabels=[]
        self.dots=[]
        self.recordData=[]
        self.polygons=[]
        self.recording=False
        self.displayChannels()

    def ghostify(self):
        if self.polygons[0].ghost:
            for polygon in self.polygons:
                polygon.ghost=False
                polygon.hide(self.prevCan)
            self.ghostifyBtn.config(text="Ghostify polygons")
        else:
            for polygon in self.polygons:
                polygon.ghost=True
                polygon.hide(self.prevCan)
            self.ghostifyBtn.config(text="UnGhostify polygons")



    def startRecording(self):
        print("start")
        self.startTime=time()
        self.recording=True
        self.recordData=[]

        self.tk.unbind("<FocusOut>")
    def showMode(self):
        for channel in self.channels:
            self.tk.bind("<KeyPress-"+self.channels[channel]["key"].lower()+">", self.genChannelTrigger(channel))
            try:
                self.tk.bind("<KeyPress-" + self.channels[channel]["key"].upper() + ">", self.genChannelTrigger(channel))
            except:
                pass
            self.tk.bind("<KeyRelease-" + self.channels[channel]["key"] + ">", self.genChannelTrigger(channel, False))

    def execCommand(self, cmd):
        if  self.serial is None:
            try:
                port=askstring("Configure serial port - Lumi", "No serial port set up. Enter name of serial port")
                if port!="":
                    self.serial=Serial(port)
                else:
                    self.serial=False
            except:
                showerror("Lumi", "Unknown serial port")
                return
        elif self.serial:
            self.serial.write(cmd.encode())
        for polygon in self.polygons:
            polygon.handle(cmd, self.prevCan)

    def triggerChannel(self, channel, state=True):
        if self.recording:
            self.recordData.append((time()-self.startTime, channel))
        print("Trigger :", channel)
        if state:
            self.execCommand(self.channels[channel]["cmd"])
        else:
            self.execCommand(self.channels[channel]["offCmd"])

        


    def genChannelTrigger(self, channel, press=True):
        return lambda e : self.triggerChannel(channel, press)

    def beginPreviewPolygon(self,e):
        "Start drawing a polygon in the preview canvas"
        self.dots=[e.x, e.y, e.x+1, e.y+1]
        self.polygon=self.prevCan.create_polygon(*self.dots, outline="white", fill="red")
        self.prevCan.bind("<Motion>", self.updatePreviewPolygon)
        self.prevCan.unbind("<Button-1>")
        self.prevCan.bind("<Button-1>", self.markPreviewPolygon)
        self.prevCan.bind("<Button-3>", self.finishPreviewPolygon)

    def updatePreviewPolygon(self, e):
        "Callback function to update preview polygon's actual point position"
        self.dots[-2]=e.x
        self.dots[-1]=e.y
        self.prevCan.coords(self.polygon, *self.dots)

    def markPreviewPolygon(self, e):
        "Mark the actual point of the preview polygon"
        self.dots+=[e.x, e.y]

    def finishPreviewPolygon(self,e):
        "Finish the preview polygon"
        self.prevCan.unbind("<Button-1>")
        self.prevCan.unbind("<Button-3>")
        self.prevCan.unbind("<Motion>")
        self.prevCan.bind("<Button-1>", self.beginPreviewPolygon)
        cmd=askstring("Bind polygon to cmd - Lumi", "Enter the polygon's ON cmd")
        offCmd = askstring("Bind polygon to cmd - Lumi", "Enter the polygon's OFF cmd")
        color=askcolor()
        self.polygons.append(Polygon(self.dots, cmd, offCmd, color[1]))
        self.dots=[]
        self.prevCan.itemconfig(self.polygon, fill="black", outline="grey")


    def validateChannel(self, oldChannel):
        "Callback function when the user validates the channel editor form"
        id=self.idEntry.get()
        label=self.labelEntry.get()
        command=self.commandEntry.get()
        offCmd=self.offCommandEntry.get()
        key=self.keyEntry.get()
        if id in self.channels and id!=oldChannel and not askokcancel("Confirmation - Lumi", "The new channel id already exists in the channels list. Overwrite ?"):
            return
        del self.channels[oldChannel]
        self.channels[id]={"label" : label, "cmd" : command, "key" : key, "offCmd" : offCmd}
        self.editor.destroy()
        self.displayChannels()

    def channelEditor(self, channel):
        "Display an editor for the given channel"
        channelInfo=self.channels[channel]
        self.editor=Toplevel(self.tk)
        Label(self.editor, text="Id : ").pack()
        self.idEntry=Entry(self.editor)
        self.idEntry.insert(0, channel)
        self.idEntry.pack()
        Label(self.editor, text="Label : ").pack()
        self.labelEntry=Entry(self.editor)
        self.labelEntry.insert(0, channelInfo["label"])
        self.labelEntry.pack()
        Label(self.editor, text="Command (on) : ").pack()
        self.commandEntry=Entry(self.editor)
        self.commandEntry.insert(0, channelInfo["cmd"])
        self.commandEntry.pack()
        Label(self.editor, text="Command (off) : ").pack()
        self.offCommandEntry = Entry(self.editor)
        self.offCommandEntry.insert(0, channelInfo["offCmd"])
        self.offCommandEntry.pack()
        Label(self.editor, text="Key : ").pack()
        self.keyEntry=Entry(self.editor)
        self.keyEntry.insert(0, channelInfo["key"])
        self.keyEntry.pack()
        self.editor.bind("<KeyPress-Return>", lambda e: self.validateChannel(channel))
        Button(self.editor, text="OK", command=lambda : self.validateChannel(channel)).pack()

    def newChannel(self):
        self.channels["untitled"]={"label" : "", "cmd" : "", "key" : "", "offCmd" : ""}
        self.channelEditor("untitled")

    def genChannelEditor(self, channel):
        "Generate and return a callback function to start an editor for the given channel"
        return lambda e: self.channelEditor(channel)

    def displayChannels(self):
        "Display all the channels in the channels frame"
        for label in self.channelsLabels:
            label.destroy()
        self.channelsLabels=[]
        for channel in self.channels:
            print(channel)
            channelInfo=self.channels[channel]
            self.channelsLabels.append(Label(self.channelsFrame, text=channelInfo["label"]+" (Id : %s, Key : %s, Command : %s)"%(channel, channelInfo["key"], channelInfo["cmd"])))
            self.channelsLabels[-1].pack()
            self.channelsLabels[-1].bind("<Button-1>", self.genChannelEditor(channel))
        self.channelsLabels.append(Button(self.channelsFrame, text="New channel", command=self.newChannel))
        self.channelsLabels[-1].pack()

    def loadDisplay(self):
        "Load a display from a .lud file"
        if askokcancel("Confirmation - Lumi", "You are about to load a display. Any unsaved changes to the actual display will be lost"):
            filename=askopenfilename(master=self.tk, title="Load Display - Lumi", filetypes=[("Lumi displays", "*.lud"), ("All files", "*")])
            with open(filename, "rb") as file:
                data=pickle.load(file)
            if "polygons" not in data:
                showerror("Error - Lumi", "The file you are trying to load is in the old lumi display format. It's not working with the new lumi version")
                return
            self.channels=data["channels"]
            self.previewImgFile=data["previewImg"]
            if self.previewImgFile:
                self.previewImg=PhotoImage(self.previewImgFile)

            self.polygons=data["polygons"]
            self.displayChannels()



    def saveDisplay(self):
        "Save actual display to a .lud file"
        filename=asksaveasfilename(master=self.tk, title="Save Display - Lumi", filetypes=[("Lumi display", "*.lud")])
        if not filename.endswith(".lud"):
            filename+=".lud"
        data={"channels" : self.channels, "previewImg" : self.previewImgFile, "polygons" : self.polygons}
        with open(filename, "wb") as file:
            pickle.dump(data, file)


    def load(self):
        "Load a synchro from a .lus file"
        pass

    def save(self):
        "Save the actual synchro to a .lus file"
        filename = asksaveasfilename(master=self.tk, title="Save Synchro - Lumi", filetypes=[("Lumi synchros", "*.lus")])
        if not filename.endswith(".lus"):
            filename += ".lus"
        print(self.recordData)
        data = self.recordData
        with open(filename, "wb") as file:
            pickle.dump(data, file)

lumi=Lumi()
lumi.tk.mainloop()
