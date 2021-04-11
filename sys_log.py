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
  
This module provides a highly targeted, specialized system logging
facility for serverless applications hosted in AWS written in Python.
You may find it preferrable to Python's standard library logging module
as it has a smaller footprint and directly injects messages into 
DynamoDB tables.

This module was designed to provide traditional system logging to
Python code run by the AWS Lambda service vs. a long-running Python
application executing in an environment with reliable access to a 
file system that is suitable for system log files. It was not 
designed to support an application that generates a high volume of 
closely-timed system logging calls.  If you have such an application 
and want to use sys_log() you will need to rework some things.  I 
suggest you start by reworking the timestamp to use milliseconds vs. 
whole seconds.

sys_log categorizes messages into multiple levels of condition 
severity. While the default levels of INFO, WARN, ALARM, and ERROR can
be easily modified keep the following two things in mind.  First, the 
different message categories flow from informational (i.e., INFORM) to 
somewhat concerning (i.e., WARN) to concerning (i.e., ALARM) to 
seriously concerning (i.e., ERROR).  Second, for a well-designed and
well-built application, system log messages on the informational side
of the spectrum will be generated far more frequently than system log 
messages on the seriously concerning side of the spectrum.  Due to this
second point, automated data lifecycle management should be put in place
to manage the DynamoDB table holding informational messages.  You will
notice a TTL attribute is created for system log messages destined for
this table.  Lifecycle management of messages contained in the DynamoDB 
table holding concerning messages should be a manual process for several 
reason (i.e., low volume, you don't want to delete messages until full 
RCA has completed). 

Usage Overview:
  0) DynamoDB
     Create tables (one for info, one for errors) each with a primary
       key named 'date' of type string and a sort key named 'stamp_mod' 
       of type string
     After data has flowed into the info messages table, dont forget to
       enable TTL using the attribute named 'expiry'
  1) In the Python module requiring system logging, import this module
     and create a global system logging object
  2) In the Python module requiring system logging, use the global 
     object to submit system logging messages
  3) Before existing the Python module, flush all of the system logging
     messages to DynamoDB tables

Be aware: 
  1) As sys_log() was designed to support serverless applications 
     running in the AWS Lambda service, diagnostic print() statements 
     are in place as they will show in CloudWatch Logs, given correct 
     configuration
     
  2) sys_log() was not designed to support a high volume of closely-
     timed system logging.  Note the 1 second delay introduced in 
     sys_log.log_message()

  3) After creating a sys_log() object, sys_log.init_issues should 
     be empty. If this list is not empty, the sys_log object will most 
     likely not work

Dependencies:
  time
  boto3
  from boto3.dynamodb.conditions import Key
  from datetime import datetime, timedelta
"""
class sys_log():
  """
  Provides specialized system logging for AWS Lambda functions, storing
  log messages in DynamoDB tables.  Assumes preexisting DynamoDB tables.
  
  if(sys_log.init_issues): 
    #some issue arose when creating the sys_log object
    
  if(sys_log.run_issues):
    #some issue arose as messages were logged or stored to Dynamo
  
  Usage:
    import sys_log
    sl = sys_log.sys_log('my_module','info_table','errors_table',
                         -6, 155520000)
    if(not sl.init_issues):
      #no issues creating the system logging object
    try:
      x = 1 / 0
    except Exception as e:
      sl.log_message('1','error','',e)
    sl.log_message('3','info','just wanted to say hi','')
    if(not sl.run_issues):
      #no issues encountered logging messages to system logging object 
    if(sl.save_messages_to_db()):
      #system logging object successfully stored all messags in Dynamo
    if(not sl.run_issues):
      #another way to check on the success of write to Dynamo
  """
  import time
  import boto3
  from   boto3.dynamodb.conditions import Key
  from   datetime                  import datetime, timedelta
 
 
  class message_core():
    """
    This class validates parameters sent to sys_log.log_message() 
    and isolates / builds the basic system log message elements that 
    will be used when assembling the complete message.
    
    if(message_core.issues): 
      #issues encountered when creating this message_core object
    """
    
 
    def __init__(self, locator, message_level, message, exception, 
                 message_types):
      """
      Args:
        locator (str) :        location within source code
        message_level(str):    system logging level (e.g., "INFO")
        message (str):         log message or '' or None
        exception (Exception): Python exception object or '' or None
        message_types[(str)]:  supported messages levels
      """
      self.issues = []
      self.message = ''
          
      if((type(locator) != str) or (locator == '')):
        self.issues.append('Invalid locator parameter')
        print('Invalid locator parameter')
      else:
        self.locator = locator
        
      if((type(message_level) != str) or (message_level == '')):
        self.issues.append('Invalid message_level parameter')
        print('Invalid message_level parameter')
      elif(not (message_level.upper() in message_types)):
        self.issues.append('Invalid message level specified')
        print('Invalid message level specified')
      else:
        self.message_level = message_level.upper()
      
      if((type(message) != str) and (message != None)):
        self.issues.append('Invalid message parameter')
        print('Invalid message parameter')
      else:
        if(message):
          self.message += message
              
      if((not isinstance(exception, Exception)) and 
         (exception != '') and (exception != None)):
        self.issues.append('Invalid exception parameter')
        print('Invalid exception parameter')
      else:
        if(exception):
          try:
            if(exception.response['Error']['Message']):
              self.message += ' ' + exception.response['Error']['Message']
            else:
              self.message += ' ' + str(exception)
          except:
            self.message   += ' ' + str(exception)
        
  
  def  __init__(self, module, info_table, errors_table, 
                tz_offset, ttl, strict=False):
    """ 
    Initialize a sys_log() object.  Pass 'True' as value for the
    keyword parameter 'strict' if you do not want auto recovery
    for invalid values supplied for the tz_offset and the ttl 
    parameters.
    
    Args:
      module       (str):  meaningful name for code in source code file
      info_table   (str):  DynamoDB table name for logginf info messages
      errors_table (str):  DynamoDB table name for logging error messages 
      tz_offset    (int):  time zone offset from UTC
      ttl          (int):  time to live for information messages
      strict       (bool): auto recover from invalid tz_offset and ttl
                           parameter values being passed in
    """
    self.NUM_SECONDS_IN = {'1 month'  : 2592200, 
                           '2 months' : 5184000, 
                           '6 months' : 155520000}
    self.MESSAGE_TYPES  = {'INFO': 1, 'WARN': 2, 'ALARM': 6, 'ERROR': 7}
    self.error_messages = {}
    self.info_messages  = {}
    self.init_issues    = []
    self.run_issues     = []
    
    tz_default  = 6             #US Central (5 or 6 hours behind UTC)
    ttl_default = self.NUM_SECONDS_IN['2 months']
      
    if((type(module) != str) or (module == '')):
      self.init_issues.append('Invalid module parameter')
      print('Invalid module parameter')
    else:
      self.module = module
      
    if((type(info_table) != str) or (info_table == '')):
      self.init_issues.append('Invalid info_table parameter')
      print('Invalid info_table parameter')
    else:
      self.info_table = info_table
      
    if((type(errors_table) != str) or (errors_table == '')):
      self.init_issues.append('Invalid errors_table parameter')
      print('Invalid errors_table parameter')
    else: 
      self.errors_table = errors_table
    
    if((tz_offset == '') or (tz_offset == None)):
      self.TZ_OFFSET = tz_default
    else:
      try:
        if(type(tz_offset) == str):
          tz_offset = int(tz_offset)
        if((type(tz_offset) != int) or (not(-13 < tz_offset < 15))):
          if(strict):
            self.init_issues.append('Invalid tz_offset parameter')
          print('Invalid tz_offset parameter')
          self.TZ_OFFSET = tz_default
        else:
          self.TZ_OFFSET = tz_offset
      except Exception as e:
        if(strict):
          self.init_issues.append('Invalid time zone offset specified. ' + 
                                  str(e))
        print('Invalid time zone_offset specified. ' + str(e))
        self.TZ_OFFSET = tz_default
        
    if((ttl == '') or (ttl == None)):
      self.TTL = ttl_default
    else:
      try:
        if(type(ttl) == str):
          ttl = int(ttl)     
        if((type(ttl) != int) or 
           (ttl < self.NUM_SECONDS_IN['1 month']) or
           (ttl > self.NUM_SECONDS_IN['6 months'])): 
          if(strict):
            self.init_issues.append('Invalid ttl parameter')
          print('Invalid ttl parameter')
          self.TTL = ttl_default
        else:
          self.TTL = ttl
      except Exception as e:
        if(strict):
          self.init_issues.append('Invalid time to live specified. ' + str(e))
        print('Invalid time to live parameter specified. ' + str(e))       
        self.TTL = ttl_default
    
    
  def reset(self):
    """
    After a function exits, the AWS Lambda service will keep the
    container used by the function around for a short time in hopes
    of reusing it for a future call to the same function.  As the
    most efficient use of sys_log() is as a global object in a module,
    you should call this method on the global object as a safe guard
    to clear out potential residual data in a case where AWS Lambda 
    is reusing a container.
    
    Additionally, you will want to use this method if you decide to
    employ a sys_log() object in a long running Python application.
    You would want to call this method after you have saved all 
    system log messages generated, so far, to Dyanmo.
    """
    self.error_messages = {}
    self.info_messages  = {}
    self.run_issues     = []
    
    
  def log_message(self, locator, message_level, message, exception):
    """
    The granularity of time stamp used is seconds vs. milliseconds.
    Inbound messages are time stamped and this stamp is used as a
    component of a key (i.e., dictionary, DynamoDB table sort key). 
    As the sort key must be unique, a 1 second time delay is 
    introduced to avoid conflicts.  Revisit this if you have an
    application that will generate a high volume of closely-timed
    systme log messages (i.e., the delay will be a performance
    so switch to milliseconds and remove the delay)

    Args:
      locator (str):        req; location inside module (source code)
      message_level (str):  req; 'INFO', 'WARN', 'ALARM', or 'ERROR' 
      message (str):        opt; free form error message or empty str
      exception(Exception): opt; Exception object or empty string
      
    Returns:
      True  successfully processed system log message
      False error occured processing system log message
    """
    results = False
    if(not self.init_issues):
      a_message_core = self.message_core(locator, message_level, message, 
                                       exception, self.MESSAGE_TYPES)
      if(not a_message_core.issues):   
        self.time.sleep(1)
        now = self.datetime.now()
        timestamp = int(now.timestamp()) #converts millisecons to seconds
        if(self.TZ_OFFSET >= 0):
          local = now - self.timedelta(hours=self.TZ_OFFSET)    #UTC -> local
        else:
          local = now + self.timedelta(hours=self.TZ_OFFSET)    #UTC -> local
        date = str(local.year) + '-' + str(local.month).zfill(2)
        date += '-' + str(local.day).zfill(2)
        stamp_mod = str(timestamp) + '+' + self.module
        
        #all pieces valid; assemble message, store in dict holding all messages
        message = (a_message_core.message_level + ': (' + 
                   a_message_core.locator + ') ' + 
                   a_message_core.message)
        if(self.MESSAGE_TYPES[a_message_core.message_level] < 
           self.MESSAGE_TYPES['ALARM']):
          expiration = timestamp + self.TTL
          self.info_messages[stamp_mod] = {'date' : date,
                                           'message' : message,
                                           'expiry' : expiration}
        else:
          self.error_messages[stamp_mod] = {'date' : date,
                                            'message' : message}
        results = True
      else:
        self.run_issues.append('One or more message_core() elements invalid')
        print('One or more message_core() elements invalid')      
    else:
      self.run_issues.append('sys_log() object invalid / inoperable')
      print('sys_log() object invalid / inoperable')
      
    return(results)
    
       
  def save_messages_to_db(self):
    """
    Write all log messages stored in sys_log's buffers to DynamoDB
    
    Returns:
      True  if no errors were encountered
      False if an error was encountered
    """
    results = True
    try:
      dynamo_db_access = self.boto3.resource('dynamodb')     
      if(self.error_messages):
        try:
          table = dynamo_db_access.Table(self.errors_table)
          for key, value in self.error_messages.items():
            table.put_item(Item={'date' : value['date'], 
                                 'stamp_mod' : key,
                                 'message': value['message']})
        except Exception as e:
          results = False
          self.run_issues.append('Exception thrown connecting / writing to ' +
            'error messages DynamoDB table.  Exception: ' + str(e))
          print('Exception thrown connecting / writing to error messages ' + 
                'DynamoDB table.  Exception: ' + str(e))
      if(self.info_messages):
        try:
          table = dynamo_db_access.Table(self.info_table)
          for key, value in self.info_messages.items():
            table.put_item(Item={'date': value['date'],
                                 'stamp_mod' : key, 
                                 'message': value['message'], 
                                 'expiry' : value['expiry']})
        except:
          results = False
          self.run_issues.append('Exception thrown connecting / writing to ' +
            'info messages DynamoDB table.  Exception: ' + str(e))
          print('Exception thrown connecting / writing to info messages ' + 
                'DynamoDB table.  Exception: ' + str(e))
    except:
      results = False
      self.run_issues.append('Could not connect to DynamoDB service')
      print('Could not connect to DynamoDB')
      
    return(results)