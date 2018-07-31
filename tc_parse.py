#!/bin/python

#
# The input files fron GCF and PTCRB has to have \t (tab) separation for elements.
#
# (c) 2018 by Jouni Korhonen
# version 0.1 - Initial
#         0.2 - Added -e / --specs switch to filter specifications
#
#
# 
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org>
#


import sys
import string
import re
import argparse

#
# The predefined regex rule for searching 3GPP specifications
# Now supported 36.521-1
#               36.521-2
#               36.521-3
#               36.523-1
#               36.523-2
#               36.523-3
#               31.121
#               31.124
#
REGEX_3GPP_SPECS = "^.*(3((6\.(521|523)-[123])|(1\.12[14])))"
NAMES_3GPP_SPECS =  ["36.521-1","36.521-2","36.521-3","36.523-1","36.523-2","36.523-3","31.121","31.124"]

# Configurations for excel parsing..

POS_PTCRB_BAND_3 = 53     # or bands
POS_PTCRB_BAND_12 = 69
POS_PTCRB_BAND_13 = 73

POS_GCF_BIM = 8
POS_GCF_BAND_3 = 10       # or bands
POS_GCF_BAND_12 = 14
POS_GCF_BAND_13 = 15
POS_GCF_BAND_20 = 16

# The SDO identification definitions

SDO_NAMES = ["Unknown","GCF","PTCRB","Both"]

SDO_UNKNOWN = 0
SDO_GCF     = 1
SDO_PTCRB   = 2
SDO_BOTH    = 3

# the band map from "real" band to a column in excel.
GCF_BAND_MAP   = { 3:10, 12:14, 13:15, 20:16 }
PTCRB_BAND_MAP = { 3:53, 12:69, 13:73 }


#
#
#

class filter:
    def __init__(self,sdo=SDO_UNKNOWN):
        if sdo not in [SDO_GCF,SDO_PTCRB,SDO_UNKNOWN]:
            raise NotImplementedError("Unknown SDO {}".format(sdo))
        
        self._sdo = sdo
        self._TCStatus = ""
        self._TCBands = {}
        self._TCUnmappedBands = []
        self._removeTDD = True
        self._removeCSG = True
        self._removeFDFDD = True
        self._specs = []

    def addTCStatus(self,tc):
        self._TCStatus += tc
    
    def addTCBand(self,band):
        self._TCUnmappedBands.append(band)

        if self.sdo() == SDO_GCF:
            if GCF_BAND_MAP.has_key(band):
                self._TCBands[band] = GCF_BAND_MAP[band]
                return

        if self.sdo() == SDO_PTCRB:
            if PTCRB_BAND_MAP.has_key(band):
                self._TCBands[band] = PTCRB_BAND_MAP[band]
                return
        print "{} has no support for band {} - ignoring".format(SDO_NAMES[self.sdo()],band)

    def getTCBand(self):
        return self._TCBands.values()
    
    def getTCStatus(self):
        return self._TCStatus
    
    def getTCUnmappedBands(self):
        return self._TCUnmappedBands

    def removeFDFDD(self,flag=None):
        if flag != None:
            self._removeFDFDD = flag
        return self._removeFDFDD

    def removeTDD(self,flag=None):
        if flag != None:
            self._removeTDD = flag
        return self._removeTDD
    
    def removeCSG(self,flag=None):
        if flag != None:
            self._removeCSG = flag
        return self._removeCSG
    
    def add3GPPSpec(self,spec):
        self._specs.append(spec)
    
    def get3GPPSpecs(self):
        return self._specs

    def sdo(self):
        return self._sdo

    def dump(self):
        print self._TCStatus
        print self._TCBands.items()


#
# Test cases are stored into a two level dictionary.
# 1. level key is the specification number
# 2. level key is the section number
#    "sdo" - string: which SDO
#    "txt" - string: test case description

_tc = {}


#
#
#
#

def applyFilters( fil, ter, std="" ):
    valid = ""
    validBands = ""

    # SDO independent filters.. this is a lame technique looking into
    # TC textual description.. it should be more generalized.

    if ter.removeTDD():
        if "TDD" in fil[2]:
            return None
    if ter.removeFDFDD():
        if re.search("FD *- *FDD",fil[2],re.IGNORECASE) is not None:
            return None
        if re.search("full *- *duplex.*FDD",fil[2],re.IGNORECASE) is not None:
            return None
    if ter.removeCSG():
        if "CSG" in fil[2]:
            return None
    if std not in ter.get3GPPSpecs():
        return None
    
    #
    valid = ter.getTCStatus()

    # There are now SDO specific ways to fill valid TCs since the source 
    # excel forms are slightly different. Not a surprised the PTCRB excel
    # is a mess and GCF is way more well behaving.
    if ter.sdo() == SDO_PTCRB:
        if valid != "":
            if fil.__len__() < POS_PTCRB_BAND_3:
                validBands = fil[5]
            else:
                validBands = fil[5]

                for band in ter.getTCBand():
                    validBands = validBands + "," + fil[band]
        
    #
    if ter.sdo() == SDO_GCF:
        # Check for invalid content found in GCF excel sheets -> a header line
        if "3GPP" in fil[1]:
            return None
        if (valid != ""):
            if (fil.__len__() <= POS_GCF_BIM):
                validBands = ""
            else:
                validBands = fil[POS_GCF_BIM]
                
                for band in ter.getTCBand():
                    validBands = validBands + "," + fil[band]

    #
    if valid == "":
        return fil
    else:
        if re.search("[{}]".format(valid),validBands.lower()) is not None:
            return fil

    return None



#
#
#


def parseLine( fh, flter ):
    sdo = flter.sdo()
    
    while True:
        s = fh.readline()

        if s == "":
            break

        # Split into an array.. the separator is \t
        lst = s.split('\t')

        # Check whether we still need to process this line.. too short lines are dropped
        if lst is None or lst.__len__() < 3:
            continue

        # Try to match against a set of known 3GPP specifications
        m = re.match(REGEX_3GPP_SPECS,lst[0]) 

        # m is None of no match was found. Also check for invalid lines by
        # looking into lst[1], which should contain the TC section number..

        if m is not None:
            spec = m.group(1)
    
            # apply further filters.. as parametrized with cli switches
            lst = applyFilters(lst,flter,spec) 
    
            if lst is None:
                continue
            
            # Clean up TC section number.. PTCRB also add "FDD" or "TDD" into the TC
            # The section can be "1.2.3.4 FDD" so just take the first part.
            sect = lst[1].split(" ",1)[0]

            # create validatin status and band lists

            # Add into dictionary and check for duplicates
            if spec not in _tc:
                # add a new dictionary entry.. there cannot be a TC section either
                _tc[spec] = { sect: { "sdo": SDO_NAMES[sdo], "txt": lst[2]} }
            else:
                # Spec exists.. check if a TC section exists
                if sect not in _tc[spec]:
                    # Nope.. add a new TC section
                    _tc[spec][sect] = { "sdo": SDO_NAMES[sdo], "txt": lst[2] }
                else:
                    # Yes.. update existing TC section
                    tc = _tc[spec][sect]

                    if tc["sdo"] == SDO_NAMES[SDO_UNKNOWN]:
                        tc["sdo"] = SDO_NAMES[sdo]
                    elif (tc["sdo"] == SDO_NAMES[SDO_BOTH]) or (tc["sdo"] == SDO_NAMES[sdo]):
                        continue
                    else:
                        tc["sdo"] = SDO_NAMES[SDO_BOTH]

#
# 
#

def dumpTC():
    for spec in _tc.keys():
        for sect in _tc[spec].keys():
            tc = _tc[spec][sect]
            print "{}\t{}\t{}\t{}".format(spec,sect,tc["sdo"],tc["txt"])

#
#
#

if __name__ == "__main__":

    p = argparse.ArgumentParser(prog=sys.argv[0], description='GCF and PTCRB Test Case parser')
    p.add_argument("-t","--keep-tdd",dest="removeTDD",help="Do not try to remove TDD TCs",action="store_false",default=True)
    p.add_argument("-f","--keep-fd-fdd",dest="removeFDFDD",help="Do not try to remove FD-FDD TCs",action="store_false",default=True)
    p.add_argument("-c","--keep-csg",dest="removeCSG",help="Do not try to remove CSG TCs",action="store_false",default=True)
    p.add_argument("-g", "--gcf", metavar="file", dest="gcfFile", help="GCF format TC list file",
                    action="store", type=str, default="")
    p.add_argument("-p", "--ptcrb", metavar="file", dest="ptcrbFile", help="PTCRB format TC list file",
                    action="store", type=str , default="")
    p.add_argument("-v", "--version", version="%(prog)s 0.1",
                    action="version") 
    p.add_argument("-b", "--bands", dest="bands", help="List of selected bands",
                    nargs="*", action="append", type=int, choices=[3,13,20], default=[] )
    p.add_argument("-s", "--gcf-status", dest="gcfStatus", help="List of GCF TC statuses",
                    nargs="*", action="append", choices=["a","b","v","e"], default=[] )
    p.add_argument("-S", "--ptcrb-status", dest="ptcrbStatus", help="List of PTCRB TC statuses",
                    nargs="*", action="append", choices=["a","b","e","p"], default=[] )
    p.add_argument("-e","--specs", dest="specs", help="List of filtered 3GPP specs - defaults to all",
                    nargs="*", action="append", choices=NAMES_3GPP_SPECS, default=None )
    args = p.parse_args()

    # parameters check..
    if args.gcfFile == None and args.ptcrbFile == None:
        p.print_help()
        sys.exit(0)

    #
    gcf = None
    ptcrb = None
    files = []

    if args.gcfFile != "":
        gcf = filter(SDO_GCF)
        files.append( (args.gcfFile, gcf) )
        
        for b in args.gcfStatus:
            for c in b:
                gcf.addTCStatus(c)

    if args.ptcrbFile != "":
        ptcrb = filter(SDO_PTCRB)
        files.append( (args.ptcrbFile, ptcrb) )
        
        for b in args.ptcrbStatus:
            for c in b:
                ptcrb.addTCStatus(c)

    #
    for name,flter in files:
        # bands per filter/sdo
        for b in args.bands:
            for c in b:
                flter.addTCBand(c)
    
        if args.specs is None:
            args.specs = [NAMES_3GPP_SPECS]

        for b in args.specs:
            for c in b:
                flter.add3GPPSpec(c)

        # global filters for sdo
        flter.removeTDD(args.removeTDD)
        flter.removeFDFDD(args.removeFDFDD)
        flter.removeCSG(args.removeCSG)

        # process file with appropriate filters
        with open(name,"r") as fh:
            parseLine(fh,flter)

    #
    dumpTC()
