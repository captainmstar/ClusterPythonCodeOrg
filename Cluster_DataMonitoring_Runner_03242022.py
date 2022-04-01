"""
Interface for CAN data monitoring Runner and showing that on the cluster 
@author Kasra <kasramokhtari@indiev.com>
"""
from collections import deque
import can
import cantools
import time
import threading
from os import path
import math
import csv
import time
from multiprocessing import Process
from apscheduler.schedulers.background import BackgroundScheduler

# Defines the paths to the dbc files for different electric components (FrontEDU, Shifter, and BMS)
path_to_dbc_FrontEDU = path.abspath(path.join(path.dirname(__file__), 'dbc', 'CANcommunicationProtocol_V1.7_20200803.dbc'))
path_to_dbc_Shifter = path.abspath(path.join(path.dirname(__file__), 'dbc', 'Arens.dbc'))
path_to_dbc_BMS = path.abspath(path.join(path.dirname(__file__), 'dbc', 'INDI_BMS_v2.dbc'))

# Defines the can interface we are using:
vectorInterface = True
kvaserInterface = False

# Defines the parameter the vehicle paramters
gearRatio =10.2
wheelsDiameter = 744*0.001   #in meter
currentTime = time.time()

# Defines initial values
currentTime = time.time()

lock = threading.Lock()

class SendCANThread(threading.Thread):
    #Creates an instance (instrument) of a CAN data Reader
    def __init__(self, instrument):
        threading.Thread.__init__(self)
        self.instrument = instrument

class Clsuter(can.Listener):
    
    

    # Creates an instance of a cluster 
    def __init__(self, channel, gearRatio, wheelsDiameter):
        # Defines the can interface that we are using
        self.bus = can.interface.Bus(bustype='vector', channel='1', bitrate=500000)
        #self.bus = can.interface.Bus(bustype='kvaser', channel='0', bitrate=500000)
        print('Connected to the CAN successfully!')
        # Reads the dbc files using Pyhton CAN library
        self.db_FrontEDU = cantools.database.load_file(path_to_dbc_FrontEDU)
        self.db_Shifter = cantools.database.load_file(path_to_dbc_Shifter)
        self.db_BMS = cantools.database.load_file(path_to_dbc_BMS)
        self.notifier = can.Notifier(self.bus, [self])
        self.threadActive = True
        self.RPM = 0
        self.vehicleSpeed = 0
        self.shifter  = 0
        self.batteryVoltage = 0
        self.batterySOC = 0
        self.batteryMode = 'DisConnected'
        self.gearRatio =10.2
        self.wheelsDiameter = 744*0.001   #in meter       

    def start(self):
        # Starts the Clsuer
        self.xmitThread = SendCANThread(self)
        self.xmitThread.start()
        
    def stop(self):
        # Ends the cluster session
        print("Stopping Cluster monitoring data")
        self.threadActive = False
        self.xmitThread.join()

    def on_message_received(self, msg: can.Message):
        # Runs this section everytime CAN receives new data (Called when a message on the bus is received)
        try:
            message_FrontEDU = self.db_FrontEDU.get_message_by_frame_id(msg.arbitration_id)
            ActRotSpd = message_FrontEDU.decode(msg.data)['MCU_ActRotSpd']
            MCU_StMode = message_FrontEDU.decode(msg.data)['MCU_StMode']
            MCU_ActTorq = message_FrontEDU.decode(msg.data)['MCU_ActTorq']
            MCU_General_ctRoll = message_FrontEDU.decode(msg.data)['MCU_General_ctRoll']
            self.RPM = ActRotSpd
            self.vehicleSpeed = ((ActRotSpd*3.6*math.pi*wheelsDiameter)/(gearRatio*60))*(0.621371)
        except:
            pass
        
        try:
            message_Shifter = self.db_Shifter.get_message_by_frame_id(msg.arbitration_id)
            Shifter_dbc = message_Shifter.decode(msg.data)['ShifterDisplay']
            self.shifter = Shifter_dbc
        except:
            pass
        
        try:
            message_BMS = self.db_BMS.get_message_by_frame_id(msg.arbitration_id)
            Voltage = message_BMS.decode(msg.data)['BatteryPackVoltage']
            self.batteryVoltage = Voltage
        except:
           pass 
        
        try:
            message_BMS = self.db_BMS.get_message_by_frame_id(msg.arbitration_id)
            BMS_Mode = message_BMS.decode(msg.data)['BMS_Mode']
            self.batteryMode = BMS_Mode
        except:
           pass 
        
        try:
            message_BMS = self.db_BMS.get_message_by_frame_id(msg.arbitration_id)
            SOC = message_BMS.decode(msg.data)['SOC']
            self.batterySOC = SOC
        except:
           pass 

    def startLog(self):
        header = ['Time', 'RPM', 'vehicleSpeed', 'shifter', 'batteryVoltage', 'batterySOC', 'batteryMode']
        # Defines name of csv file 
        self.filename = "clusterLogger.csv"
            
        # writing to csv file 
        with open(self.filename, 'w', newline='') as csvfile: 
            # Creates a csv writer object 
            self.csvwriter = csv.writer(csvfile)     
            # Writes the fields 
            self.csvwriter.writerow(header)  
                
    def updatelog(self):    
        # Writes the data rows 
        data = [time.time()-currentTime, self.RPM, self.vehicleSpeed, self.shifter, self.batteryVoltage, self.batterySOC, self.batteryMode]
        with open(self.filename, 'a', newline='') as csvfile:  
            self.csvwriter = csv.writer(csvfile)    
            self.csvwriter.writerow(data)     

if __name__ == "__main__":
    print('Initializing the Cluster...')
    clusterRunner = Clsuter(0, gearRatio, wheelsDiameter)
    clusterRunner.start()
    clusterRunner.startLog()
    sched = BackgroundScheduler()
    # Logs the data every 10 seconds
    sched.add_job(clusterRunner.updatelog, 'interval', seconds=0.1)
    sched.start()
    print('Data is been logged into a csv file...')
    while True:
        time.sleep(1.0)
