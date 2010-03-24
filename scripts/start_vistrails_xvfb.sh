#!/bin/bash

#settings
LOG_DIR=/server/wiki/vistrails/main/vistrails/logs
Xvfb_CMD=/usr/X11R6/bin/Xvfb
VIRTUAL_DISPLAY=":7"
Xvfb_PARAM="$VIRTUAL_DISPLAY -screen 0 1280x960x24"
VISTRAILS_DIR=/server/wiki/vistrails/main/vistrails/trunk/vistrails
ADDRESS="vistrails.sci.utah.edu"
PORT="8080"
NUMBER_OF_OTHER_VISTRAILS_INSTANCES=1
MULTI_OPTION="-M"
if (("$#" > "0")); then
    VIRTUAL_DISPLAY="$1"
fi
if (("$#" > "1")); then
    ADDRESS="$2"
fi
if (("$#" > "2")); then
    PORT="$3"
fi
if (("$#" > "3")); then
    NUMBER_OF_OTHER_VISTRAILS_INSTANCES="$4"
fi
if (("$#" == "5")); then
   if(("$5" == "0")); then
       MULTI_OPTION=""
   else
       MULTI_OPTION="-M"
   fi
fi

PID="$LOG_DIR/pid$VIRTUAL_DISPLAY.vistrails"
LOG_XVFB="$LOG_DIR/xvfb$VIRTUAL_DISPLAY.log"

#try to find Process ID of running X-Server
echo "checking if Xvfb is already running..."
echo "ps -eaf | grep $Xvfb_CMD | grep $VIRTUAL_DISPLAY | awk '{print \$2}'"
pid=`ps -eaf | grep $Xvfb_CMD | grep $VIRTUAL_DISPLAY | awk '{print \$2}'`
if [ "$pid" ]; then
    echo "Xvfb already running [pid=${pid}]"
else
    #start a virtual server
    if [ -x $Xvfb_CMD ]; then
	$Xvfb_CMD $Xvfb_PARAM>& $LOG_XVFB &
	
	sleep 5

	#Make sure it started
	pid=`ps -eaf | grep $Xvfb_CMD | grep $VIRTUAL_DISPLAY | awk '{print $2}'`
	if [ "$pid" ]; then
	    echo "done."
	else
	    echo "FAILED."
	fi
    else
	echo "Error: Could not find $Xvfb_CMD. Cannot start Xvfb."
    fi
fi
echo -n "Starting VisTrails in Server Mode on display $VIRTUAL_DISPLAY.0 - "
cd $VISTRAILS_DIR
export DISPLAY=$VIRTUAL_DISPLAY
python stop_vistrails_server.py http://$ADDRESS:$PORT
python vistrails_server.py -T $ADDRESS -R $PORT -O$NUMBER_OF_OTHER_VISTRAILS_INSTANCES $MULTI_OPTION&
echo $! > $PID

