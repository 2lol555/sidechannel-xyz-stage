# CPA Framework

Framework for side-channel attacks through power consumption using the Correlation Power Analysis (CPA) attack method. This implementation includes attacks on AES-128 and ASCON-128. As a baseline were used scripts developed by [Leo Weissbart](https://leoweissbart.github.io/) and [Łukasz Michał Chmielewski](https://scholar.google.com/citations?user=OV1OwgYAAAAJ&hl=en), provided by the [CESCA Lab](https://cescalab.cs.ru.nl).

## How to set up:

### Install Python 3.13.2
   
Download and unzip
```bash
cd /tmp
wget https://www.python.org/ftp/python/3.13.5/Python-3.13.5.tgz
tar -xvf Python-3.13.5.tgz
cd Python-3.13.5
```

Install required libraries and compile Python
```bash
sudo apt install -y build-essential libssl-dev libffi-dev libbz2-dev liblzma-dev libsqlite3-dev libreadline-dev libncurses5-dev zlib1g-dev tk-dev libgdbm-dev libdb5.3-dev libexpat1-dev
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall
```

Check if it is correctly installed
```bash
python3.13 --version
```
  
### Setup venv and clone repo
   
```bash
cd ~
git clone https://github.com/Qas1modo/CPA-Framework
cd CPA-Framework
mkdir venv
python3.13 -m venv ./venv
```

Activate venv (temporary)

```bash
source ./venv/bin/activate
```

### Install packages

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install numpy
python -m pip install numba
python -m pip install trsfile
python -m pip install tqdm
python -m pip install pandas
python -m pip install scipy
python -m pip install matplotlib
```

### Set up PYTHONPATH to project root
   
Temporary
```bash
export PYTHONPATH="~/CPA-Framework:$PYTHONPATH"
```
Permanent
```bash
echo 'export PYTHONPATH="~/CPA-Framework:$PYTHONPATH"' >> ~/.bashrc
```

Sometimes this does not work with '~', specify full path when it happens.

### Install libraries for measurement script (Optional)
```bash
python -m pip install smartleia
git clone https://github.com/cw-leia/smartleia-target
cd smartleia-target
python3 -m pip install .
cd ..
rm -rf ./smartleia-target
python3 -m pip install picosdk
python3 -m pip install pycryptodome
```

## How to use:

### Configuration

All user configuration is located in [the Configuration](Configuration) folder.
Modify relevant files and their values to match your preferences.

 - [AES config](Configuration/AesConfiguration.py) to configure AES attack.
 - [Alignment config](Configuration/AlignmentConfiguration.py) to configure directly started [Alignment](AttackTools/Alignment.py).
 - [ASCON config](Configuration/AsconConfiguration.py) to configure ASCON attack.
 - [ASCON Trace Gen config](Configuration/AsconTraceGenConfiguration.py) to configure trace generator.
 - [Constants](Configuration/Constants.py) are used to store global constants, but they can be updated if necessary.
 - [Measurement Script Constants](Configuration/MeasurementScriptConstants.py) are used to store constants needed in measurement scripts, and can be updated if necessary.
 - [Measurement Script JavaCard config](Configuration/MeasurementScriptJCConfiguration.py) used to set up measurement script for JavaCard.
 - [Resampler config](Configuration/ResamplerConfiguration.py) to configure directly started [Resampler](AttackTools/Resampler.py).
 - [TVLA config](Configuration/TvlaConfiguration.py) configures Test Vector Leakage Assessment(TVLA).

### What you can run

 - [Alignment](AttackTools/Alignment.py) ⇒ Perform alignment based on your [config](Configuration/AlignmentConfiguration.py).
 - [Resampler](AttackTools/Resampler.py) ⇒ Resample traces based on your [preferences](Configuration/ResamplerConfiguration.py).
 - [Trace Converter](Utilities/TraceConverter.py) ⇒ Convert or cut trace sets based on your preferences inside the file.
 - [Trace Printer](Utilities/TracePrinter.py) ⇒ Print metadata and sample snippets from a trace set based on your preferences inside the file.
 - [Trace Visualizer](Utilities/TraceVisualizer.py) ⇒ Interactively visualise traces based on your preferences inside the file.
 - [TVLA](Tvla/Tvla.py) ⇒ Run TVLA on TraceSet specified in this [config](Configuration/TvlaConfiguration.py).
 - [AES Attack](Aes/AesKeyExtractor.py) ⇒ Run AES attack based on your preferences from [config](Configuration/AesConfiguration.py).
 - [ASCON Attack](Ascon/AsconKeyExtractor.py) ⇒ Run ASCON attack based on your preferences from [config](Configuration/AsconConfiguration.py).
 - [ASCON Trace Gen](Ascon/ProofOfConcept/AsconTraceGenerator.py) ⇒ Run Trace Generator to create traces for leakage detection testing based on your preferences from [config](Configuration/AsconTraceGenConfiguration.py).
 - [Measurement Script JavaCard](MeasurementScripts/MeasureScriptPicoscopeJC.py) ⇒ Measurement script used to capture power traces from JavaCard by Picoscope, configured from [here](Configuration/MeasurementScriptJCConfiguration.py).
   
### Use the framework

If you want to use the framework for a new SCA attack, you can use [Generics](Common/Generics) by inheritance.
 - [Generic Attacker](Common/Generics/GenericAttacker.py) ⇒ Has the necessary functionality to perform SCA attack (automatic alignment, ...).
 - [Generic Extractor](Common/Generics/GenericExtractor.py) ⇒ Helps you with running the attack on multiple targets and prints results.
 - [Generic Logger](Common/Generics/GenericLogger.py) ⇒ Helps you with logging the attack performance.
 - [Generic Parallel Writer](Common/Generics/GenericParallelWriter.py) ⇒ Has the functionality to parallelly write/read TRS, NPY and NPZ files.
 - [Generic Trace Loader](Common/Generics/GenericTraceLoader.py) ⇒ Implement reading of TRS, NPY and NPZ files with their metadata.
 - [Generic Trace Writer](Common/Generics/GenericTraceWriter.py) ⇒ Implement reading/writing of TRS, NPY and NPZ files with their metadata.
 - [Generic Trace Creator](Common/Generics/GenericTraceCreator.py) ⇒ Used to create traces in TRS, NPY and NPZ file formats without input files.
