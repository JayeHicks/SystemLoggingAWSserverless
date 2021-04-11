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

This module provides a simple mechanism to send out alert messages
from a Python module.  Currently, only supports AWS SNS communication
channel but the designa allows other channels to be easily added.

Usage:
  0) set up all of the requisite alert messaging endpoints (e.g., AWS 
     SNS topics)
  1) In the Python moudle that imports this module, create a 
     send_alerts() object, supplying all requisite detail
  2) interrogate the send_alrerts() object to determine the success
     / failure of both object initialization and message transmission
  
Be aware: 
1) As send_alerts() was designed primarly to support Python code
   running as an AWS Lambda service function.  Diagnostic print()
   statements are in place as they will display in CloudWatch Logs, 
   provided proper configuration

2) Processing a high volume of closely-timed alert messages was not 
   a design goal of send_alerts()

3) Post creation, a send_alerts() object offers a list of strings that
   will be empty if no issues were encountered.  If initiatization or
   message submission encountered any issues, they will be captured in
   this list.

Dependencies:
  boto3
"""
class send_alerts():
  """
  Specialized alert messaging for AWS Lambda functions written in 
  Python
    
  The send_alerts.__init__() takes a single parameter.  A single
  parameter can accomodate multiple messages.  Each message can
  be sent to one or more recipients.
  
  Usage:
    import send_alerts
    param = [{'channel':'sns', 'message':'an alert message', 
      'topic_arns':['arn:aws:sns:us-east-1:12345678901:MyAlert']}]
    a_sm = send_alerts(param)
    if(a_sm.issues): 
      #issue(s) occured during initialization or sending message(s)
  """
  import boto3
  
  
  def _send_sns_messages(self, param):
    """
    Send a single message to one or more AWS SNS topics.  The message
    will be published to all topics even if an individual publish for
    a topic fails.  However, all publishing to topics will stop if an
    exception is thrown, even if subsequent publish calls after the
    exception would have succeeded.
       
    Args:
      param  [{})]: required.  example parameter:
        [{'channel':'sns', 
          'message':'an alert message', 
          'topic_arns':['arn:aws:sns:us-east-1:12345678901:MyAlert']}]
    """  
    try:
      sns_access = self.boto3.client('sns')
      for arn in param['topic_arns']:
        print('Sending to: ' + arn + ' a message of: ' + param['message'])        
        resp = sns_access.publish(TargetArn=arn,
                                  Message=param['message'])
        if(resp['ResponseMetadata']['HTTPStatusCode'] != 200):
          error_code = str(resp['ResponseMetadata']['HTTPStatusCode'])
          self.issues.append('Response from publish to sns topic indicates ' +
                             'failure. HTTPStatusCode: ' + error_code)
          print('Response from publish to sns topic indicates ' + 
                'failure. HTTPStatusCode: ' + error_code)
        else:
          print('Successfully published message to topic: ' + arn)
    except Exception as e:
      self.issues.append('Exception while publishing to sns topic. ' +
                         'Exception involving: ' + str(e))
      print('Exception while publishing to sns topic. Exception ' +
            'involving: ' + str(e))
          

  def _validate_sns_message(self, param):
    """
    Future exercise: determine canonical AWS SNS arn and use RE to 
    validate incoming a little more rigorously
    
    Args:
      param  [{})]: required.  example parameter:
        [{'channel':'sns', 'message':'an alert message', 
         'topic_arns':['arn:aws:sns:us-east-1:12345678901:MyAlert']}]
          
    Return:
      True  if everything checks out
      False if an issue was uncovered
    """  
    results = True
    
    try:     
      if((type(param['message']) != str) or (param['message'] == '')):
        results = False
        self.issues.append('Invalid message parameter for sns alert message')
        print('Invalid message parameter for an sns alert message')
      
      if((type(param['topic_arns']) != list) or (not param['topic_arns'])):
        results = False
        self.issues.append('Empty or invalid list of topic arns supplied')
        print('Empty or invalid list of sns topic arns supplied')
      
      for arn in param['topic_arns']:
        if((type(arn) != str) or (arn == '') or ('arn' not in arn) or  
           ('aws' not in arn) or ('sns' not in arn)):
          results = False
          self.issues.append('Invalid sns topic arn specified')
          print('Invalid sns topic arn specified')
    except Exception as e:
      results = False
      self.issues.append('Exception thrown involving: ' + str(e))
      print('Exception thrown involving: ' + str(e))
    return(results)
  
  
  def  __init__(self, params):
    """ 
    Initialize object and process all messages.  Process all messages
    even if an invalid message is encountered.  After successful 
    creation of a send_alerts object, the object will provide a list 
    named 'issues' that can be checked to determine if an issues 
    occured with either initialization or message transmission.
    
    Args:
      param  [{})]: required.  example parameter:
        [{'channel':'sns', 'message':'an alert message', 
         'topic_arns':['arn:aws:sns:us-east-1:12345678901:MyAlert']}]
    """
    self.supported_channels = ['sns']
    self.issues             = []
    
    try:
      if(params):
        for param in params:
          if(param['channel'] in self.supported_channels):
            if(param['channel'] == 'sns'):
              if(self._validate_sns_message(param)):
                self._send_sns_messages(param)
              
            #future: add additional distribution channels here
          else:
            self.issues.append('Unrecognized message distribution channel ' +
                               'specified')
            print('Unrecognized message distribution channel specified')  
    
      else:
        self.issues.append('Attempt to create send_alerts object with an ' +
                           'empty input parameter')
        print('Attempt to create send_alerts object with an empty input ' + 
              'parameter')
    except Exception as e:
      self.issues.append('Exception thrown involving: ' + str(e))
      print('Exception thrown involving: ' + str(e))