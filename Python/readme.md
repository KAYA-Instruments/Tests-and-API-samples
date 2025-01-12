# Python API Samples & Test Cases
This section provides Python-based test and API samples for working with the Vision Point API.

## Minimum requirements
1. **Python 3.6 (64-bit)** installed on your system.  
   > ⚠️ **Note:** Using a 32-bit Python version may result in errors when loading the DLL.
2. **KAYA Instruments Vision Point** software installed.

## Running the Sample
Execute the following command in your terminal:  
```bash
python3 KYFGLib_API_Sample.py
```

In case parameterization is needed, e.g. for selecting frame grabber device index:
```bash
python3 KYFGLib_API_Sample.py --deviceIndex 0
```

## Test case return codes

| **Name**            | **Value** | **Comment**                                           |
|---------------------|-----------|-------------------------------------------------------|
| `SUCCESS`           | 0         | Case succeeded                                        |
| `COULD_NOT_RUN`     | 1         | Case couldn’t run                                     |
| `NO_HW_FOUND`       | 2         | Required hardware was not found                       |
| `NO_REQUIRED_PARAM` | 3         | A required parameter wasn’t provided                  |
| `WRONG_PARAM_VALUE` | 4         | An unacceptable value was specified for a parameter   |

If the returned code is not `SUCCESS`, the case output should provide more details.