import paramiko
import time
from enum import Enum
import sys
sys.path.append('../PythonUtilities')
import CFGFileHelper
import ThreadHelper
from colorama import init, Fore, Back, Style
from tkinter import *
import threading
from collections import OrderedDict 

pi = None 
pi_select_list = []
py_ver = '3.6.5'
pip_ver = 'pip3.6'

# Store username and password in a pi.ini file with the below format:
#[pi]
#username = xxxxxx
#password = xxxxxxx
login_cfgpath = '../Private/pi.ini'
logindict = CFGFileHelper.read_raw(login_cfgpath, 'pi')
username = logindict['username']
password = logindict['password']
#print(username)
#print(password)

cfgpath = 'rpi_updater.ini'
pidict = CFGFileHelper.read_raw(cfgpath, 'Raspberry Pi')
RPILIST = [*pidict] # get list of keys
cfgdict = CFGFileHelper.read_raw(cfgpath, 'Config')
std_apt_install = cfgdict['std_apt_install']
std_pip_install = cfgdict['std_pip_install']
purge_list = cfgdict['purge_list']
#print(RPILIST)
#print(std_apt_install)
#print(std_pip_install)
#print(purge_list)

def list_to_string(listname):
    liststring = ", ".join(listname)
    return liststring

class Com(Enum):
    pip_update_all = pip_ver+" freeze --local | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 sudo "+pip_ver+" install -U"
    pip_upgrade_pip = "sudo "+pip_ver+" install --upgrade pip"
    pip_install = "sudo "+pip_ver+" install"
    pip_remove = "sudo "+pip_ver+" uninstall"
    pip_list_outdated = "sudo "+pip_ver+" list --outdated"
    pip_freeze = pip_ver+"freeze"
    apt_update = "sudo apt-get -y update"
    apt_upgrade = "sudo apt-get -y upgrade"
    dist_upgrade = "sudo apt-get -y dist-upgrade"
    rpi_upgrade = "sudo rpi-update"
    reboot = "sudo reboot"
    autoremove = "sudo apt-get -y autoremove"
    autoclean = "sudo apt-get -y autoclean"
    clean = "sudo apt-get -y clean"
    purge = "sudo apt-get -y remove --purge "
    
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
sys_action_dict["Send Terminal Command"] = ["pi.send_ssh_command", "Send Terminal Command", 'insert_textbox']
sys_action_dict["RPi Update"] = ["pi.update", "Raspberry Pi Updates:\n apt-get update, apt-get upgrade, apt-get dist-upgrade, rpi-update"]
sys_action_dict["RPi Install Single Apt Package"] = ["pi.apt_install", "Installs Single Package", 'insert_textbox']
sys_action_dict["RPi Standard Module Install"] = ["pi.apt_install", "Installs packages: \n"+list_to_string(std_apt_install)]
sys_action_dict["Purge RPi Bloatware"] = ["pi.purge", "Removes packages: \n"+list_to_string(purge_list)]
sys_action_dict["RPi Autoremove & Autoclean"] = ["pi.autoremove_and_autoclean", "RPi Autoremove & Autoclean"]
sys_action_dict["Install Single Python Module"] = ["pi.pip_install", "Installs Single Python Module", 'insert_textbox']
sys_action_dict["Remove Single Python Module"] = ["pi.pip_remove", "Removes Single Python Module", 'insert_textbox']
sys_action_dict["Install Standard Python Modules"] = ["pi.pip_install", "Installs Python Modules:\n"+list_to_string(std_pip_install)]
sys_action_dict["Pip List Outdated Modules"] = ["pi.pip_list_outdated", "Lists outdate Python Modules"]
sys_action_dict["Pip Upgrade All"] = ["pi.pip_update_all", "Updates all installed Python Modules:\n"+Com.pip_update_all.value ]
sys_action_dict["Upgrade Pip Utility"] = ["pi.upgrade_pip", "Upgrades Pip utility:\n"+Com.pip_upgrade_pip.value]
sys_action_dict["Install Python "+py_ver] = ["pi.install_python", "Install Python "+py_ver]
sys_action_dict["Reboot RPi"] = ["pi.reboot", "Reboot RPi"]
        
class SSHClass():
    ssh = None
    def __init__(self, name, username, password):
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.username = username
        self.password = password
        self.name = name
        self.ip = pidict[name]
    
    def connect(self):
        print(Fore.YELLOW+'\nConnecting to '+ self.name + " (" + self.ip+ ")")
        try:
            self.ssh.connect(self.ip, username=self.username, password=self.password, allow_agent = False)
            #print(self.ssh)
        except:
            print(Fore.YELLOW+'Failed to connect to '+self.name)
       
    def write(self, cmd, autoprompt=False, waitforinput=True):
        if isinstance(cmd, Enum):
            cmd = cmd.value
        out = None
        print(Fore.CYAN+"\n>> Executing: "+cmd)
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
                        elif "Proceed (y/n)?" in line:
                            self.stdin.write("Y\n")   
                            self.stdin.flush()
        print(Fore.CYAN+">> Done executing command")
    
    
    def write_sequence(self, cmdlist, autoprompt=False):
        """Run a list of commands"""
        for cmd in cmdlist:
            self.write(cmd, autoprompt)
    
    def send_ssh_command(self, cmd):
        #cmd = app.retrieve_ssh_input()
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
        
    def upgrade_pip(self):
        self.write(Com.pip_upgrade_pip)
                    
    def purge(self, package=None):
        if not package:
            package = " ".join(purge_list)
        cmd = Com.purge.value+" "+package
        self.write(cmd)
        self.write(Com.clean)
        self.autoremove_and_autoclean()
        
    def pip_update_all(self):
        self.write(Com.pip_update_all)
                    
    def pip_list_outdated(self):
        self.write(Com.pip_list_outdated)
        
    def pip_install(self, module=None, upgrade=True):
        """Takes a module Enum, list of string module names, or single module string name"""
        basecmd = Com.pip_install.value+" "
        if not module:
            module = std_pip_install
        #print(module)
        cmdlist = []
        if isinstance(module, Enum):
            #print('Module is enum')
            cmd = basecmd + module.value
            if upgrade:
                cmd += " --upgrade"
            cmdlist.append(cmd)
        elif isinstance(module, list):
            #print('Module is list')
            for mod in module:
                cmd = basecmd + mod
                if upgrade:
                    cmd += " --upgrade"
                cmdlist.append(cmd)
            for cmd in cmdlist:
                self.write(cmd, autoprompt=True)
        else:
            #print('Module is string')
            cmd = basecmd + module
            if upgrade:
                cmd += " --upgrade"
            self.write(cmd, autoprompt=True)

    def pip_remove(self, module=None):
        """Takes a module Enum, list of string module names, or single module string name"""
        basecmd = Com.pip_remove.value+" "
        #print(module)
        cmdlist = []
        if isinstance(module, Enum):
            #print('Module is enum')
            cmd = basecmd + module.value
            cmdlist.append(cmd)
        elif isinstance(module, list):
            #print('Module is list')
            for mod in module:
                cmd = basecmd + mod
                cmdlist.append(cmd)
            for cmd in cmdlist:
                self.write(cmd, autoprompt=True)
        else:
            #print('Module is string')
            cmd = basecmd + module
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

@ThreadHelper.threaded
def run():
    global pi_select_list
    pi_select_list = app.retrieve_pi_select_input()
    testlist = app.retrieve_pi_sys_input()
    #testlist += app.retrieve_pi_py_input()
    #print(testlist)
    
    for key in pi_select_list:
        pi = SSHClass(key, username, password)
        pi.connect()
        app.set_pi_text_color(RPILIST.index(key), "green", "yellow")    
        for test in testlist:
            arg = None
            if isinstance(test, list):
                arg = test[1]
                test = test[0]
                #print(test)
                #print(arg)

            #print("Test="+str(test))
            execfunc = eval(test)
            for action, item in sys_action_dict.items():
                if item[0] == test:
                    index = list(sys_action_dict.keys()).index(action)
            app.set_cb_text_color(index, "green", "yellow")
            if arg:
                execfunc(arg)
            else:
                execfunc()
            app.set_cb_text_color(index)
        app.set_pi_text_color(RPILIST.index(key))

pi = SSHClass("Homecontrol", username, password)

class App(threading.Thread):
    status = None
    ssh = None
    cli = None
    button1_state = False
    options = None
    pady=8
    padx=8
    cb_pady=1
    cb_padx=1
    width=20
    bg_color = "cyan"
    font_sm = ("Helvetica", 10)
    font_md = ("Helvetica", 12)
    font_lg = ("Helvetica", 16)
    action_cb_list = []
    frame = []
    tb = []
    action_cb = []
    index = 0
             
    def __init__(self):
        threading.Thread.__init__(self)
        self.start()
        
    def callback(self):
        self.root.quit()
       
    def exit(self):
        self.root.quit()
        
    def update_status(self, newstatus, goodnews=True):
        if goodnews:
            self.status.config(fg="green")
        else:
            self.cs_status.config(fg="red") 
        self.status["text"] = newstatus
              
    def get_textbox(self, index):
        if self.tb[index]:
            return self.tb[index].get() 
        else:
            return None
        
    def set_pi_text_color(self,index,fg_color='SystemWindowText',bg_color='SystemButtonFace'):
        #print(self.pi_cb[index]['fg'])
        #print(self.pi_cb[index]['bg'])
        self.pi_cb[index]['fg']=fg_color
        self.pi_cb[index]['bg']=bg_color
  
    def set_cb_text_color(self,index,fg_color='SystemWindowText',bg_color='SystemButtonFace'):
        #print(self.pi_cb[index]['fg'])
        #print(self.pi_cb[index]['bg'])
        self.action_cb[index]['fg']=fg_color
        self.action_cb[index]['bg']=bg_color
              
    #def retrieve_ssh_input(self):
        #return self.ssh.get() 
   
    def retrieve_pi_select_input(self):
        self.active_list = []
        i = 0
        for var in self.pi_cb_list:
            x = var.get()
            if x == 1:
                self.active_list.append(RPILIST[i]) 
            i+=1
        return self.active_list 
 
    def retrieve_pi_sys_input(self):
        self.sys_list = []
        self.action_list = list(sys_action_dict.keys())
        i = 0
        for var in self.action_cb_list:
            value = var.get()
            if value == 1:
                key = self.action_list[i]
                action = sys_action_dict[key][0]
                if self.tb[i]:
                    tx =self.get_textbox(i)
                    self.sys_list.append([action,tx])
                else:
                    self.sys_list.append(action)
            i+=1
        #print(self.sys_list)
        return self.sys_list 
        
    def update_mouseover_text(self, text=""):
        self.info["text"] = text
    
    def create_checkboxes(self, row, action_dict):
        for key in action_dict:
            textbox = False
            self.action_cb_list.append(IntVar())
            if len(action_dict[key]) == 3:
                if action_dict[key][2] == 'insert_textbox':
                    textbox = True

            if len(action_dict[key]) > 1:
                action_text = key
                mouseover_text = action_dict[key][1]
            else:
                action_text = key
                mouseover_text = key
            
            self.frame.append(Frame(self.root))
            self.frame[self.index].grid(row=row,column=0, columnspan=2, pady=0,padx=0, sticky=W)
        
            #self.action_cb[i] = Checkbutton(self.root, text=action_text, variable=self.action_cb_list[i])
            self.action_cb.append(Checkbutton(self.frame[self.index], text=action_text, variable=self.action_cb_list[self.index]))
            self.action_cb[self.index].grid(row=row, column=0, sticky=W, pady=self.cb_pady,padx=self.cb_padx)
            self.action_cb[self.index].bind("<Enter>", lambda event, t=mouseover_text: self.update_mouseover_text(text=t))
            self.action_cb[self.index].bind("<Leave>", lambda event: self.update_mouseover_text(text=''))
            
            if textbox:
                self.tb.append(Entry(self.frame[self.index],width=20, font=self.font_sm, justify=LEFT))
                self.tb[self.index].grid(row=row,column=1,pady=self.cb_pady,padx=self.cb_padx, sticky=W)
                self.tb[self.index].delete(0, END)
                self.tb[self.index].insert(0, "")
            else:
                self.tb.append(None)
            row+=1
            self.index+=1

        return row-1
            
    def run(self):
        self.root = Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.callback)
        self.root.geometry("400x700") #Width x Height

        # Pi selection
        row_start1 = 1
        row_span1=4
        frame_height1 = (row_span1 * 25 ) + (row_span1 * self.pady) 
       
        # Maintenance section
        row_start2 = row_start1 + row_span1
        row_span2 = 6
        frame_height2 = (row_span2 * 25 ) + (row_span2 * self.pady) 
        
        #separator1 = Frame(self.root, width=640, height=frame_height1, bd=4, padx=3, pady=3, relief=GROOVE).grid(column=0, columnspan=2, row=row_start1, rowspan=row_span1)
        #separator2 = Frame(self.root, width=640, height=frame_height2, bd=4, padx=3, pady=3, relief=GROOVE).grid(column=0, columnspan=2, row=row_start2, rowspan=row_span2)
    
        r = 0
        label = Label(self.root, text="Raspberry Pi Update Utility", font=self.font_lg)
        label.grid(row=r,column=0, columnspan=2, sticky=W)
 
        r += 1
        label = Label(self.root, text="Raspberry Pi Selection", font=self.font_md)
        label.grid(row=r,column=0, columnspan=2, sticky=W)
        
        r += 1
        self.pi_cb_list = []
        self.pi_cb = [None]*len(RPILIST)
        i = 0
        for key in RPILIST:
            #self.pi_select.insert(END, item)
            self.pi_cb_list.append(IntVar())
            action_text = key
            mouseover_text = pidict[key]
            self.pi_cb[i] = Checkbutton(self.root, text=action_text, variable=self.pi_cb_list[i])
            self.pi_cb[i].grid(row=r, sticky=W)
            self.pi_cb[i].bind("<Enter>", lambda event, t=mouseover_text: self.update_mouseover_text(text=t))
            self.pi_cb[i].bind("<Leave>", lambda event: self.update_mouseover_text(text=''))
            r+=1
            i+=1
        
        r += 1
        label = Label(self.root, text="System Actions", font=self.font_md)
        label.grid(row=r,column=0, columnspan=2, sticky=W)
        
        r += 1
        r = self.create_checkboxes(r, sys_action_dict)
           
        r += 1
        self.button_run = Button(self.root, width=self.width, bg=self.bg_color, text="Run", font=self.font_sm, command=run)
        self.button_run.grid(row=r,column=0,pady=self.pady,padx=self.pady, rowspan=1)
        
        self.button_exit = Button(self.root, width=self.width, bg=self.bg_color, text="Exit", font=self.font_sm, command=exit)
        self.button_exit.grid(row=r,column=1,pady=self.pady,padx=self.pady, rowspan=1)
        
        r += 1
        self.info = Label(self.root, justify=LEFT, font=self.font_sm, text="", wraplength=400)
        self.info.grid(row=r,column=0, columnspan=2, rowspan=3, sticky=W)
        
        self.root.mainloop()
 
app = App()




