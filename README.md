# SystemLoggingAWSserverless
System logging facility for AWS Lambda functions written in Python.  With a minimal footprint and message storage in DynamoDB, ideal for AWS-based serverless applications.

# Introduction
On occasion I am commissioned by a client to extend a POC into a hardened, productized solution.  To meet some of the requisite operational support functionality, I  developed this custom system logging framework for AWS-based solutions.  My top design goals included a small / focused footprint and the storage of log messages in DynamoDB.  This system logging solution can be used to coordinate system logging across an entire serverless application or across any collection of Python modules that you care to instrument.

At a high-level, after you have created a couple of DynamoDB tables, all that is required is the instrumentation of your Python modules with calls to the system logging facility.  If you create the logging facility as a global object within the module (recommended), you will not have to change any preexisting Python code (e.g., function / class parameter list).  However, you must understand the implications of using a global object and take the appropriate steps.  This includes calling sys_log.reset() when your Python module is run as an AWS Lambda function or when your Python module is a long-running application.

# Overview
This system logging solution partitions messages into two broad categories, each utilizing a separate DynamoDB table.  System logging messages are presumed to range along a severity continuum from innocuous, informational messages all the way to catastrophic failure.  Within each of the two broad categories, an arbitrary number of sub categories can introduced to represent the progression along the severity continuum.

* Informational Messages
  * Messages intended to range from “informative” all the way to up to “warning”
  * Relative high volume when compared to error messages
    * sys_log() provides automated data lifecycle management for these messages, which you can customize
  * sys_log provides default sub categories
      * “INFO” and “WARN” 
      * You can customize the name, number, and meaning of subcategories
* Error Messages 
  * Messages intended to range from “error” to “catastrophic”
  * Relatively low volume when compared to informational messages
    * Manual data lifecycle management required for these messages; you don’t want these messages disappearing until you have concluded root cause analysis
  * sys_log() provides default sub categories
    * “ALARM” and “ERROR”
    * You can customize the name, number, and meaning of subcategories

Within the Python module using sys_log() to store a system log message you must supply several pieces of information.
* Locator
  * Required
  * A unique identifier enabling you to pinpoint, within the Python module, where a given system logging message was generated.  I find that unique, positive integers work well
  * Absolutely essential when submitting certain types of system log messages
    * The system log messages submitted does not have a string value for Message Text.  The only thing supplied is a Python run-time exception object which makes it hard to figure out exactly which specific sys_log() call, that only supplies a Python run-time exception object, generated the message
    * There are multiple system log message submissions that supply an identical, a very similar, Message Text (or Python run-time exception object)
    * The system log messages submitted uses a variable, instead of a literal string, to pass along a value for Message Text.  In this case you wont a literal string in the source code; the error message will be contained by the variable (e.g., importing errors/issues from an external module such as send_alerts)
  * Take great care not to duplicate these identifiers that you use for the locator value.  Any modern text editing tool can help you easily determine if you have any duplicate locators in your module.
  * I suggest using a special identifier notation in cases where error messages originate outside of the immediate module (e.g., from a send_alerts() object created within the Python module).
* Message Level
  * Required
  * The severity level for the message.  The default severity continuum is “INFO”, “WARN”, “ALARM”, “ERROR.”
  * You are free to completely customize the number, name, and meaning of sub categories for the system logging message categories
* Message Text
  * Can be literal text string, an empty string, None, or a variable containing a string.
  * Will be concatenated in front of the textual representation of the Python run-time exception (if one is supplied)
* Python Run-Time Exception Object
  * Can by a run-time Python exception object, empty string, or None
  * Textual representation of the Python run-time exception, if supplied, will be concatenated after the Message Text parameter (if supplied).

In order to use sys_log() within a Python module, the following must occur and occur in the following order.
* Create two DynamoDB tables (one for informational messages and one for error messages)
* Import the sys_log module into the Python module
* Create a global sys_log() object and provide the following information at creation time
  * The name of the Python module that you are instrumenting with sys_log()
  * The name of the informational messages DynamoDB table
  * The name of the error messages DynamoDB table
  * Optionally you may choose to specify
    * A time zone offset from UTC.  For US Standard Time you would supply 5 or 6.  sys_log() does not automatically adjust to US daylight savings time.  If you’d like sys_log time stamps to account for daylight savings time you can manually switch alternate offset values twice a year or you can add complexity to the sys_log() class.
    * A time to live value (in seconds) for informational messages.  The default value is two months.
* In the function that serves as the entry point for the Python module that you are instrumenting with sys_log()
  * Check to ensure that the global sys_log() object was created successfully
  * Clear out residual data from the global sys_log() object, just in case the AWS Lambda servcie is reusing a warm container
  * During the execution flow of control, of the entire Python module, use global sys_log() object to submit system log messages
  * Before you exit this function (i.e., the entire module), flush all of the system log messages that have been submitted to the DynamoDB tables.  After the flush you can check the global object to detect issues that occurred during the write to DynamoDB.

# Details
## Design
By providing a Python module global object as the interface to the system logging facility, you can leave existing Python source code as is (e.g., function / class parameter list).  However, this strategy requires that certain precautions be taken when the Python module is run by the AWS Lambda service or is a long running process.  You must take care to clear out previous system log messages from the global object’s internal buffers post sys_log.save_to_db().  A call to sys_log. reset(), at the appropriate time, will handle issues introduced by:
* The AWS Lambda service will keep the container used by an exiting function around for a limited time in hopes of reusing the container for a future call to the same function
* A long running Python process will bring up a single global sys_log() object and reuse it in perpetuity

Neither the sys_log() class nor the send_alerts() calss was designed for high-volume, closely-timed usage.  If you would like to use either class in this manner you will, at the very least, need to change sys_log.log_message() so that the time stamp uses milliseconds vs whole seconds and the time delay is in milliseconds vs a whole second.

## Set Up DynamoDB Tables
Set up two DynamoDB tables, one for informational messages and one for error messages.  For both designate an attribute named “date” as the partition key and an attribute named “stamp_mod” as the sort key.  After data has populated the informational message table enable “Time To Live” and specify the “expiry” attribute.

## Example use of sys_log() and send_alerts()
The following can be used as a reference for canonical use of the sys_log() and send_alerts() classes.
'''
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
    '''
