import sys
import pysvn
import serial
import time
from string import split
from math import sin, exp


class ArduinoRGB(object):
    startBytes = 1
    def __init__(self, com_port="COM4", speed=9600):
        self.serial = serial.Serial(com_port, speed)
        
    def convert_to_bytes(self,intList):
        """
        Using the defined number of 'startBytes' convert the list of ints to bytes
        appropriate for sending to the Arduino.
        """
        retStr = chr(255)*self.startBytes + "".join([chr(i) for i in intList])
        return retStr

    def set_colors(self, red, green, blue):
        """
        Set the RGB LED to the colors provided, values should be between 0 and 254.
        """
        self.serial.write(self.convert_to_bytes([red, green, blue]))
                          
class SubversionMonster(object):
    #These values have worked well, but will continue to tweak them.
    scalar_modifier = 4
    time_modifier = 20.0
    time_limit = 3*60*60 #Three hours
    total_range = 200
    
    def __init__(self, arduino=ArduinoRGB(), verbose=True, username=None, password=None):
        self.arduino = arduino
        self.svn_client = pysvn.Client()
        self.current_rev = None
        self.verbose = verbose
        if username and password:
            #If a username and password are provided, set the callback.  We don't need to use the params
            #passed in.
            self.svn_client.callback_get_login = lambda x,y,z: (True, username, password, True)

    #I feel like there's a better way to do these color functions, but this works and produces a nice effect.
    def greenVal(self, value):
        if value < 2*self.total_range/3.0:
            return 0
        else:
            value =  value - 2*(self.total_range/3.0)
            return (254.0/(self.total_range/3.0))*value
    def redVal(self, value):
        if value < self.total_range/3.0:
            return 254 - (254.0/(self.total_range/3.0))*value
        else:
            return 0
    def blueVal(self, value):
        if value < self.total_range/2.0:
            return (254.0/(self.total_range/2.0))*value
        else:
            value =  value - self.total_range/2.0
            return 254.0 - (254.0/(self.total_range/2.0))*value
    def get_RGB_values(self,inp):
        """
        This will return the appropriate rgb values based on the input value.
        The input is between 0 and 200 with 0 being totally red, 100 being totally
        blue and 200 being totally green.  Intermediate values are a mix.
        TODO: This could be moved to the Arduino class.
        """
        inp = int(min(inp, self.total_range))
        print [self.redVal(inp), self.blueVal(inp), self.greenVal(inp)]
        return [min(254, self.redVal(inp)), min(254, self.blueVal(inp)), min(254,self.greenVal(inp))]

    def productivity_point(self, minutes, lines):
        """
        Using the scalar_modifier and time_modifier calculate the contribution of a single commit, given
        the number of minutes since it occurred.
        """
	#Note: The min makes the maximum commit 'size' 500.
        return self.scalar_modifier*min(lines, 500)*exp(-(minutes/self.time_modifier))

    def calculate_score(self,commits):
        """
        Given a list of time_diffs (in minutes) and lines changed, calculate the 'productivity' score
        Input is a list of tuples (time_diff, lines_changed)
        """
        return sum([self.productivity_point((time.time() - c[0])/60,c[1]) for c in commits])

    def update_repo(self, p):
        """
        Update the repo contained in p and return the latest revision.
        """
        return self.svn_client.update(p)[0]

    def get_diff_count(self, p, rev1, rev2):
        """
        Given a path or url and two revisions, return the number of lines changed between rev1 and rev2.
        
        Note: Line of diff doesn't exactly yield number of lines altered, but it's a good enough measure of commit size.
        """
        return len(split(self.svn_client.diff('./temp', p, revision1=rev1, revision2=rev2),'\n'))
    
    def get_commit_time(self, p, rev):
        return self.svn_client.info2(p, revision=rev)[0][1]['last_changed_date']
        
    def get_initial_values(self, p):
        """
        Update the repo and get all commits that have occurred within the time limit.
        """
        self.current_rev = self.update_repo(p)
        current_time = time.time()
        commits = []
        for i in range(self.current_rev.number, 1, -1):
            rev1 = pysvn.Revision( pysvn.opt_revision_kind.number, i-1 )
            rev2 = pysvn.Revision( pysvn.opt_revision_kind.number, i )
            commit_time = self.get_commit_time(p, rev2)
            if (current_time - commit_time) > self.time_limit:
                break

            changedLines = self.get_diff_count(p, rev1, rev2)
            commits.append((commit_time, changedLines, rev2))
        #We want the commits in reverse order, so the newest one is the last entry in the list.
        commits.reverse()
        return commits


    def monitor(self,p):
        commits = self.get_initial_values(p)
        while 1:
            if len(commits) == 0:
                #No action in the last 3 hours, uh oh...  Keep checking until we get some action
                if self.verbose:
                    print "No action in the last 3 hours"
                while (self.current_rev.number == self.update_repo(p).number):
                    for i in range(30):
                        #Go into blinking mode.  This is something that should be moved to the Arduino itself.
                        self.arduino.set_colors(254,0,0)
                        time.sleep(.5)
                        self.arduino.set_colors(0,0,0)
                        time.sleep(.5)
            latest_rev = self.update_repo(p)
            if latest_rev.number != self.current_rev.number:
                commits.append((self.get_commit_time(p, latest_rev),
                                self.get_diff_count(p, self.current_rev, latest_rev),
                                latest_rev))
                self.current_rev = latest_rev

            #Get rid of any old commits
            for c in commits:
                if self.verbose:
                    print "%d lines %d minutes ago" % (c[1], (time.time() - c[0])/60)
                if (time.time() - c[0]) > self.time_limit:
                    commits.remove(c)
            score = self.calculate_score(commits)
            if self.verbose:
                print "Score", score
            self.arduino.set_colors(*self.get_RGB_values(score))
            time.sleep(20)


def testRGB():
    svnMon = SubversionMonster()
    while 1:
        for i in range(100):
            svnMon.arduino.set_colors(*svnMon.get_RGB_values(i))
            print i
            time.sleep(0.1)

if __name__ == "__main__":
    repo_path = sys.argv[1]
    svnMon = SubversionMonster() 
    svnMon.monitor(repo_path)