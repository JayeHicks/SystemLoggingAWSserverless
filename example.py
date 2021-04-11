"""
Jaye Hicks
Obligatory legal disclaimer:
  You are free to use this source code (this file and all other files 
  referenced in this file) "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER 
  EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THIS SOURCE CODE
  IS WITH YOU.  SHOULD THE SOURCE CODE PROVE DEFECTIVE, YOU ASSUME THE
  COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION. See the GNU 
  GENERAL PUBLIC LICENSE Version 3, 29 June 2007 for more details.

Python module with example use of sys_log class for system logging
and send_alerts class for sending alert messages to end users.  while
the actual Python source code statements are arbitrary and nonsensical,
the module demonstrates canonical use of sys_log and send_alerts.

If this module were run as an AWS Lambda function, with configuration,
print() statements will show up in CloudWatch Logs.  If the system
logging object itself is having issues you can't use it to capture 
messages about the issues.  Instead, you send these messages to 
CloudWatch Logs using print() statements.
"""
import boto3

import sys_log
import send_alerts

#global object that supports system logging throughout entire module
sl = sys_log.sys_log('example','info_table','errors_table','','')


def function1():
  """
  arbitrary code illustrating use of sys_log and send_alerts
  """
  results = False
  if(False):
    results = True
    sl.log_message('5', 'INFO', 'everythign is OK', '') 
  else:
    #example of custom message and without a Python Exception object
    sl.log_message('6','ERROR', 'terrible error occured', '')
    
    #example of use of send_alerts()
    params = [{'channel' : 'sns',
               'message' : 'terrible error occurred',
               'topic_arns':['arn:aws:sns:us-east-1:123456789012:MyAlerts']}]
    alert = send_alerts.send_alerts(params)
    
    #example of ingesting error captured outside this module into sys_log()
    if(alert.issues):
      for issue in alert.issues:
        sl.log_message('7+', 'ERROR', issue, '')  #note special location indicator
                                                  #noting that issue originated
                                                  #outside of module
  return(results)


def example():
  """
  All functions in this module use the sys_log global object to record
  system logging messages. Because the flow of control for executing
  this module begins and ends with this specific function, use this
  function to ensure that the following happens and happens in order.
  See the sequence numbers embedded in the inline comments.
  
  1) Handle potential failure of initializing the sys_log object. If
     you cannot cleanly create the sys_log object you most likely will
     not want to continue with with normal execution of this module.
  2) Call the sys_log.reset() method to take care of the potential case 
     in which the AWS Lambda service is reusing a warm container to run
     this module
  3) After all of this module's processing has concluded, save the 
     system logging messages, collected in the global object, to the 
     DynamoDB tables
  4) Handle potential failures that occured during the execution of the
     sys_log object (either accepting messages or the final write of
     the messages to the DynamoDB tables)
     
  NOTE: With proper configuration, print() statements will show up in
        CloudWatch Logs for Lambda functions.  So thats how to log a
        message when issues arise with sys_log() itself
  """
  if(not sl.init_issues):    #1) detect failure initializing sys_log object
                             #   see additional comment below for step 1)
    sl.reset()               #2) clear potential data from previous execution
	
    """*************************************************************
	  Here is where you would start the normal processing flow for the
    funciton / module.  The following are arbitrary example uses of 
    the sys_log object
    *************************************************************"""
    try:
      s3_access_client = boto3.client('s3')
      s3_access_client.head_bucket(Bucket='my-bucket')  #someone else owns
    except Exception as e:                              #will throw a 403
      sl.log_message('3', 'ERROR', '', e)
        
    if(not function1()):
      sl.log_message('8', 'WARN', 'function1() didnt complete successfully','')
    """***************************************************************
    end of normal processing flow / example uses of sys_log object
    ***************************************************************"""    

    sl.save_messages_to_db()    #3) all processing concluded, time to write
                                #   system logging messages to DynamoDB
    
    if(sl.run_issues):          #4) if run time issues occured with sys_log
                                #   object, one or more print() statements
    
      #Option A: single print() statement
      print('One or more issues arose while sys_log object processed ' +
            'messages or saved messages to DynamoDB tables')
      
      #Option B: separate print() statement for each issue
      #for issue in sl.run_issues:
      #  print('sys_log runtime issue arose: ' + issue)
    
  else:                       #1) if initialization issues occured with sys_log
                              #   object, one or more print() statements
                              
    #Option A: single print() statement
    print('One or more issues arose while sys_log object was being ' +
          'created / initialized.')
    #Option B: separate print() statement for each issue
    #for issue in sl.init_issues:
    #  print('sys_log init issue arose: ' + issue)