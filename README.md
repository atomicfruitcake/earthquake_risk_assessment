# Earthquake Risk Assessment

This application is used to calculate the risk of an earthquake across
the continental Unites States.

The earthquake_risk_assessor.py module contains a set of functions that
are used to fetch the earthquake data from the USGS website and process 
that data to compare the number of earthquakes by US states and then check
the risk of each client location.


## Examples
### Example 1
This tackles the first aim in the task. It produces a list of all states that 
had earthquakes in the last week sorted by number of earthquakes. The example 
script then writes this to the console in a human readable format.

### Example 2
This tackles the second aim in the task. It finds all nearby earthquakes to the
client locations and gives a risk score based on the number and magnitude of the 
earthquakes nearby. For this, arbitrary values were used for what constitutes the
risk and significant proximity of the earthquakes 

## Requirements
- python == 3.13.2
- pip == 23.2.1

Please note lower versions of Python may work, but your mileage may vary

## Installing dependencies
From the root of this directory run
```bash
pip install -r requirements.txt
```

## Running the examples
Run:
```bash
python example.py
```

## Running Tests
Run:
```bash
python -m unittest discover -s ./ -p 'test.py'
```

## Notes
- The application currently uses earthquake data for the past week.
These were added as variables so can be adjusted as required. If more historical
data was needed, this would then be paginated when fetching data.
- The approach taken was to use as much pure Python as possible rather
that relying on libraries
- There is no error handling if the API calls to the GeoLookup or USGS APIs fails, in
a production app this would have a retry/backoff algorithm to be defensive