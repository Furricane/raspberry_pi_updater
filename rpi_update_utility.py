import paramiko
import time
from enum import Enum
import sys
sys.path.append('../PythonUtilities')
import CFGFileHelper
import ThreadHelper
from tkinter import *
import threading
from collections import OrderedDict 

pi = None 
pi_select_list = []
py_ver = '3.6.5'
pip_ver = 'pip3.6'

cfgpath = '../Private/pi.ini'
logindict = CFGFileHelper.read_raw(cfgpath, 'pi')
username = logindict['username']
password = logindict['password']

print(username)
print(password)

class Com(Enum):
    pip_update_all = pip_ver+" freeze --local | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 sudo "+pip_ver+" install -U"
    pip_upgrade_pip = "sudo "+pip_ver+" install --upgrade pip"
    pip_freeze = pip_ver+"freeze"
    apt_update = "sudo apt-get -y update"
    apt_upgrade = "sudo apt-get -y upgrade"
    dist_upgrade = "sudo apt-get -y dist-upgrade"
    rpi_upgrade = "sudo rpi-update"
    reboot = "sudo reboot"
    autoremove = "sudo apt-get -y autoremove"
    autoclean = "sudo apt-get -y autoclean"
    clean = "sudo apt-get -y clean"
    remove_bloatware = "sudo apt-get -y remove --purge dillo wolfram-engine scratch* nuscratch sonic-pi idle3 smartsim java-common minecraft-pi python-minecraftpi python3-minecraftpi libreoffice* gpicview oracle-java8-jdk openjdk-7-jre oracle-java7-jdk openjdk-8-jre"
    
       
RPI = { "Homecontrol" : '192.168.1.91',
        "Camera" : '192.168.1.92',
        "Plexserver" : '192.168.1.95' }
 
RPILIST = [*RPI] # get list of keys
    
print("SSH Interface to Raspberry Pi")


# List of apt-get install 
std_apt_install = ['fonts-droid-fallback', 'openssl', 'libssl-dev', 'python3-tk', 'python3-dev', 'python3-matplotlib', 'conky']

# List of python modules to install with pip
std_pip_install = ['schedule', 'colorama', 'requests', 'pyserial', 'httplib2', 'google-api-python-client',
                 'sleekxmpp', 'pubnub',  'urllib3', 'pychromecast', 'plexapi']
                
# these take a while, don't need to be on every Pi
add_pip_install = ['numpy', 'matplotlib','pandas']
                
# Sequence to install Python3.6

python36_install = ['sudo apt-get -y install libssl-dev',
                    'sudo cd /',
                    'sudo pwd',
                    'sudo cd /usr/src',
                    'sudo pwd',
                    'sudo wget https://www.python.org/ftp/python/'+py_ver+'/Python-'+py_ver+'.tgz',
                    'sudo tar xzvf Python-'+py_ver+'.tgz',
                    'sudo cd Python-'+py_ver+'/',
                    'sudo ./configure',
                    'sudo make -j4',
                    'sudo make altinstall' ]


sys_update_list = [Com.apt_update, Com.apt_upgrade, Com.dist_upgrade, Com.rpi_upgrade]

sys_action_dict = OrderedDict() 
sys_action_dict["Send SSH Command"] = "pi.send_ssh_command"
sys_action_dict["Pi Update (apt-get update, apt-get upgrade, apt-get dist-upgrade, rpi-update)"] = "pi.update"
sys_action_dict["Pi Standard Module Install ("+str(std_apt_install)+")"] = "pi.apt_install"
sys_action_dict["Remove Bloatware"] = "pi.remove_bloat"
sys_action_dict["Pi Autoremove & Autoclean"] = "pi.autoremove_and_autoclean"
sys_action_dict["Reboot Pi"] = "pi.reboot"

py_action_dict = OrderedDict() 
py_action_dict["Upgrade Pip Utility ("+Com.pip_upgrade_pip.value+")"] = "pi.upgrade_pip"
py_action_dict["Install Modules ("+str(std_pip_install)+")"] = "pi.pip_install"
py_action_dict["Pip Upgrade All"] = "pi.pip_update_all"
py_action_dict["Install Python "+py_ver] = "pi.install_python"
        
class SSHClass():
    ssh = None
    def __init__(self, ip, username, password):
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.name = ip
        self.ip = ip
        self.username = username
        self.password = password
        if isinstance(ip, Enum):
            self.name = ip.name
            self.ip = ip.value
        else:
            self.name = ip
            self.ip = RPI[ip]
    
    def connect(self):
        print('\nConnecting to '+ self.name + ", " + self.ip)
        try:
            self.ssh.connect(self.ip, username=self.username, password=self.password, allow_agent = False)
            #print(self.ssh)
        except:
            print('Failed to connect to '+self.name)
       
    def write(self, cmd, autoprompt=False, waitforinput=True):
        if isinstance(cmd, Enum):
            cmd = cmd.value
        out = None
        print("\n>> Executing: "+cmd)
        self.stdin, self.stdout, self.stderr  = self.ssh.exec_command(cmd, get_pty=True) 
        if waitforinput:
            while not self.stdout.channel.exit_status_ready():
                for line in iter(self.stdout.readline, ""):
                    print(line, end="") 
                    if autoprompt:        
                        if "Press any key to continue" in line: 
                            self.stdin.write("\n")
                            self.stdin.flush()
                        elif "Do you want to continue" in line: 
                            self.stdin.write("Y\n")   
                            self.stdin.flush()
        print(">> Done executing command")
    
    
    def write_sequence(self, cmdlist, autoprompt=False):
        """Run a list of commands"""
        for cmd in cmdlist:
            self.write(cmd, autoprompt)
    
    def send_ssh_command(self):
        cmd = app.retrieve_ssh_input()
        self.write_sequence([cmd])
        
    def root_login(self):
        self.write('/bin/su root -l',waitforinput=False)
        while not self.stdout.channel.exit_status_ready():
            print(stderr.readline())
            self.stdin.write(password+'\n')
        
    def update(self):
        self.write_sequence(sys_update_list, autoprompt=True)
        
    def autoremove_and_autoclean(self):
        self.write(Com.autoremove)
        self.write(Com.autoclean)
        
    def remove_bloat(self):
        self.write(Com.remove_bloatware)
        self.write(Com.clean)
        self.autoremove_and_autoclean()

    def upgrade_pip(self):
        self.write(Com.pip_upgrade_pip)
                    
    def pip_update_all(self):
        self.write(Com.pip_update_all)
                    
    def pip_install(self, upgrade=False, module=None):
        """Takes a module Enum, list of string module names, or single module string name"""
        basecmd = 'sudo '+pip_ver+' install '
        if not module:
            module = std_pip_install
        #print(module)
        cmdlist = []
        if isinstance(module, Enum):
            print('Module is enum')
            cmd = basecmd + module.value
            if upgrade:
                cmd += " --upgrade"
            cmdlist.append(cmd)
        elif isinstance(module, list):
            print('Module is list')
            for mod in module:
                cmd = basecmd + mod
                if upgrade:
                    cmd += " --upgrade"
                cmdlist.append(cmd)
            for cmd in cmdlist:
                self.write(cmd, autoprompt=True)
        else:
            print('Module is string')
            cmd = basecmd + module
            if upgrade:
                cmd += " --upgrade"
            self.write(cmd, autoprompt=True)

    def apt_install(self, module=None):
        """Takes a module Enum, list of string module names, or single module string name"""
        basecmd = 'sudo apt-get -y install '
        if not module:
            module = std_apt_install
        cmdlist = []
        if isinstance(module, Enum):
            cmd = basecmd + module.value
            cmdlist.append(cmd)
        elif isinstance(module, list):
            for mod in module:
                cmd = basecmd + mod
                cmdlist.append(cmd)
            for cmd in cmdlist:
                self.write(cmd, autoprompt=True)
        else:
            cmd = basecmd + module
            self.write(cmd, autoprompt=True)  
   
    def install_python():
        pi.write_sequence(python36_install) 
             
    def reboot(self):
        self.write(Com.reboot)

def run():
    global pi_select_list
    pi_select_list = app.retrieve_pi_select_input()
    testlist = app.retrieve_pi_sys_input()
    
    for key in pi_select_list:
        #key = RPILIST[key]
        pi = SSHClass(key, username, password)
        pi.connect()
       # pi.write_sequence(['ls','pwd'])
        
        for test in testlist:
            print(test)
            #index = app.action_list.index(test)
            #print(index)
            #testname = app.actions[index]
            execfunc = eval(test)
            execfunc()
        #while True:
            #pass

pi = SSHClass("Homecontrol", username, password)
    
class App(threading.Thread):
    status = None
    ssh = None
    cli = None
    button1_state = False
    options = None
 
    def __init__(self):
        threading.Thread.__init__(self)
        self.start()
 
    def callback(self):
        self.root.quit()
       
    def update_status(self, newstatus, goodnews=True):
        if goodnews:
            self.status.config(fg="green")
        else:
            self.cs_status.config(fg="red") 
        self.status["text"] = newstatus
              
    def toggle_open(self):
        if self.button1_state:
            self.button1['fg']='green'
            self.button1['text']='Close Button'
            self.button1_state = False
        else:
            self.button1['fg']='red'
            self.button1['text']='Open Button'
            self.button1_state = True

    def retrieve_ssh_input(self):
        return self.ssh.get() 
   
    def retrieve_pi_select_input(self):
        self.active_list = []
        i = 0
        for var in self.pi_cb_list:
            x = var.get()
            if x == 1:
                #print(RPILIST[i]+" is active")
                self.active_list.append(RPILIST[i])
            i+=1
        print(self.active_list)
        return self.active_list 
 
    def retrieve_pi_sys_input(self):
        self.sys_list = []
        self.action_list = list(sys_action_dict.items())
        #print(action_list)
        i = 0
        for var in self.action_cb_list:
            value = var.get()
            if value == 1:
                key = self.action_list[i][0]
                action = self.action_list[i][1]
                print(key)
                print(action)
                #print(RPILIST[i]+" is active")
                self.sys_list.append(action)
            i+=1
        print(self.sys_list)
        return self.sys_list 
   
    def retrieve_pi_py_input(self):
        self.py_list = []
        self.py_action_list = list(py_action_dict.items())
        #print(action_list)
        i = 0
        for var in self.py_action_cb_list:
            value = var.get()
            if value == 1:
                key = self.py_action_list[i][0]
                action = self.py_action_list[i][1]
                print(key)
                print(action)
                #print(RPILIST[i]+" is active")
                self.py_list.append(action)
            i+=1
        print(self.py_list)
        return self.py_list 
                    
    def run(self):
        self.root = Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.callback)
 
        pady=8
        padx=8
        
        cb_pady=1
        cb_padx=1
        
        width=20
        
        bg_color = "cyan"
        font = ("Helvetica", 10)
        
        # Pi selection
        row_start1 = 1
        row_span1=4
        frame_height1 = (row_span1 * 25 ) + (row_span1 * pady) 
       
        # Maintenance section
        row_start2 = row_start1 + row_span1
        row_span2 = 6
        frame_height2 = (row_span2 * 25 ) + (row_span2 * pady) 
        
        #separator1 = Frame(self.root, width=640, height=frame_height1, bd=4, padx=3, pady=3, relief=GROOVE).grid(column=0, columnspan=2, row=row_start1, rowspan=row_span1)
        #separator2 = Frame(self.root, width=640, height=frame_height2, bd=4, padx=3, pady=3, relief=GROOVE).grid(column=0, columnspan=2, row=row_start2, rowspan=row_span2)
    
        #self.options = StringVar(self.root)
        #self.options.set(PI_LIST[0]) # default value

        r = 0
        label = Label(self.root, text="Raspberry Pi Update Utility", font=("Helvetica", 16))
        label.grid(row=r,column=0, columnspan=2, sticky=W)
 
        r += 1
        label = Label(self.root, text="Raspberry Pi Selection", font=("Helvetica", 12))
        label.grid(row=r,column=0, columnspan=2, sticky=W)
        
  
        r += 1
        self.pi_cb_list = []
        i = 0
        for item in RPILIST:
            #self.pi_select.insert(END, item)
            self.pi_cb_list.append(IntVar())
            Checkbutton(self.root, text=item, variable=self.pi_cb_list[i]).grid(row=r, sticky=W)
            r+=1
            i+=1
        
        r += 1
        label = Label(self.root, text="System Actions", font=("Helvetica", 12))
        label.grid(row=r,column=0, columnspan=2, sticky=W)
        
        r += 1
        self.ssh = Entry(self.root,width=20, font=font, justify=LEFT)
        self.ssh.grid(row=r,column=1,pady=cb_pady,padx=cb_padx, sticky=W)
        self.ssh.delete(0, END)
        self.ssh.insert(0, "")
        
        #f1 = tk.Frame(root)
        #b1 = tk.Button(f1, text="One button")
        #b2 = tk.Button(f1, text="Another button")

        self.action_cb_list = []
        i = 0
        for action in sys_action_dict:
            self.action_cb_list.append(IntVar())
            Checkbutton(self.root, text=action, variable=self.action_cb_list[i]).grid(row=r, sticky=W, pady=cb_pady,padx=cb_padx)
            r+=1
            i+=1
            
 
        # Python Actions
        r += 1
        label = Label(self.root, text="Python Actions", font=("Helvetica", 12))
        label.grid(row=r,column=0, columnspan=2, sticky=W)
        
        r += 1
        #self.ssh = Entry(self.root,width=20, font=font, justify=LEFT)
        #self.ssh.grid(row=r,column=1,pady=pady,padx=padx, sticky=W)
        #self.ssh.delete(0, END)
        #self.ssh.insert(0, "")
        
        self.py_action_list = []
        self.py_actions = ["pi.install_python"]

        self.py_action_cb_list = []
        i = 0
        for action in py_action_dict:
            self.py_action_cb_list.append(IntVar())
            Checkbutton(self.root, text=action, variable=self.py_action_cb_list[i]).grid(row=r, sticky=W, pady=cb_pady,padx=cb_padx)
            r+=1
            i+=1
            
   
        r += 1
        self.button_pi_select = Button(self.root, width=width, bg=bg_color, text="Run", font=font, command=run)
        self.button_pi_select.grid(row=r,column=0,pady=pady,padx=padx, rowspan=1)
        
        self.root.mainloop()
 
app = App()




