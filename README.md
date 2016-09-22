![Chicago Bikeshare Logo](/assets/108px_logo.png)
# Chicago Bikeshare

A skill for Amazon Alexa<br>
http://www.alexaskillstore.com/

## Overview

This skill lets you check the status of stations in the Chicago
Divvy bike sharing network. You can request the number of bikes,
docks, or both from any specific station. Use the station name,
such as "Orleans Street and Elm Street" or "Adler Planetarium"
to make the request. Station names are displayed at the stations
themselves and on the Divvy website. The names are generally either
the nearest cross-street or a nearby significant landmark. If you
only remember one street name, you can say "Alexa, ask Chicago 
bikeshare what stations are on Grand" (or whatever the street is)
for a list of all stations on that street.

To easily check the status of stations you use every day, the
Chicago Bikeshare skill will let Alexa remember an origin and
destination address. If you choose to store an address, Alexa
will be able to give you the number of bikes available at the
station closest to your origin and the number of docks at the
station closest to your destination. If there's not many left,
it will also check the next nearest station.

Ask Alexa to remember a new address with
"Alexa, ask Chicago bikeshare to save an address", or change
an existing address with
"Alexa, ask Chicago bikeshare to change an address". You can
also refer to your origin address as "home", and your destination
as "work" or "school".

Once Alexa remembers your origin and destination addresses, all
you need to do is to say "Alexa, ask Chicago bikeshare to check 
my commute", and you'll know if you need to use your backup station!

You can always check what address(es) you have stored with, e.g.,
"tell me which home address is saved". Remove all stored addresses
by saying "remove my addresses".

This skill is not sponsored by, endorsed by, or affiliated with
Divvy Bikes. For more information about Divvy, visit their website at
http://www.divvybikes.com/.

## Things you can say

- Alexa, ask Chicago Bikeshare how many bikes are at the Ashland Avenue and Grand Avenue station.
- Alexa, ask Chicago Bikeshare to check my commute.
- Alexa, ask Chicago Bikeshare to store an address.
- Alexa, ask Chicago Bikeshare to tell me what work address is set.
- Alexa, tell Chicago Bikeshare to remove my addresses.
- Alexa, ask Chicago Bikeshare what stations are on State Street.
- Alexa, ask Chicago Bikeshare the status of Fairbanks Court and Grand Avenue.
- Alexa, ask Chicago Bikeshare about Grand and Fairbanks.

## Developer Notes

This code is designed to run in an AWS Lambda function.
You'll need to also include the `requests` and `boto3` modules
in the zip file sent to AWS. (AWS Lambda functions include `boto3`
in the environment, but only v1.3. This Skill needs v1.4.)

The skill requires an additional `config.py` file in the "divvy" folder.
This file should define the following attributes at global level:
- APP_ID : The unique ID of the Skill which uses the Lambda
- divvy_api : Web address of the Divvy API. As of September 2016, this is https://feeds.divvybikes.com/stations/stations.json.
- maps_api : Web address of the Google Maps Geocoding API (used when users store addresses). As of September 2016, this is https://maps.googleapis.com/maps/api/geocode/.
- maps_api_key : Token which allows access to the Google Maps Geocoding API
- aws_region : Region in which you have your database
- db_type : Database backend for storing addresses. Either 's3' or 'dynamo'.
- user_table : If using DynamoDB, the table name which stores address data
- bucket_name : If using S3, the bucket name which stores address data
- key_prefix : If using S3, a prefix to keys holding address data

### Developer Requirements

In addition to requirements listed in the `requirements.txt`, developers
should also have the following packages installed
- mock
- pytest