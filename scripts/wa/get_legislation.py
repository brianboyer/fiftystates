#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from lxml.html import parse

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

#this parser ignores the chamber parameter and always gets everything for both chambers
#
#in wa, three-digit-numbered bills are initiatives and have the same number in both the upper and lower chambers
#
#other data we could be collecting:
#   amendments http://dlr.leg.wa.gov/billsummary/default.aspx?Bill=1010&year=1995
#   if the legislation is a bill or an initiative http://dlr.leg.wa.gov/billsummary/default.aspx?year=2005&bill=330&chamber=H
#   fiscal notes http://dlr.leg.wa.gov/billsummary/default.aspx?year=2005&bill=1098
#   actions have associated bill versions http://dlr.leg.wa.gov/billsummary/default.aspx?year=2005&bill=1098

class WALegislationScraper(LegislationScraper):

    state = 'wa'

    def scrape(self, year):
      
        #get bills by topic search page -- gives a list of bill IDs per year
        bills_url = 'http://apps.leg.wa.gov/billsbytopic/default.aspx?year=%s' % (year)
        print bills_url
        bills = parse(bills_url).getroot()
        for option in bills.cssselect('select#ucDefault_talCriteria option'):
            number = option.text
            
            #three-numbered bills are initiatives, same number in both chambers
            if len(number) == 3:
                self.scrape_bill(year, number, 'H')
                self.scrape_bill(year, number, 'S')
            else:
                self.scrape_bill(year, number)
    
    def scrape_bill(self, year, number, initiative_chamber = None):
        
        #initiatives are in both chambers under the same number
        if initiative_chamber:
            summary_url = 'http://dlr.leg.wa.gov/billsummary/default.aspx?Bill=%s&year=%s&chamber=%s' % (number, year, initiative_chamber)
        else:
            summary_url = 'http://dlr.leg.wa.gov/billsummary/default.aspx?Bill=%s&year=%s' % (number, year)
          
        #get bill summary  
        print summary_url
        summary = parse(summary_url).getroot()
        
        #will be HB, SB, HI, or SI
        if summary.cssselect('span#ctl00_contentRegion_lblShortBillID')[0].text.startswith('H'):
            chamber = "lower"
        else:
            chamber = "upper"
        session = year #correct??
        title = summary.cssselect('span#ctl00_contentRegion_lblBriefDescription')[0].text
        self.add_bill(chamber, session, number, title)
        
        #get bill versions
        versions = summary.cssselect('td[style*="dashed"] a[href*="/Pdf/Bills"]')
        for version in versions:
            self.add_bill_version(chamber, session, number, version.text, version.get('href'))
            
        sponsors = summary.cssselect('td:contains("Sponsors:") span.ObviousLink a')               
        for sponsor in sponsors:
            self.add_sponsorship(chamber, session, number, 'cosponsor', sponsor.text)
        
        page_actions = []
        action_year = 0
        for row in summary.cssselect('tr#ctl00_contentRegion_trPlaceHolder>td>table>tr'):
            
            header_cell = row.cssselect('td[colspan="3"] b')
            if len(header_cell) > 0:
                header = header_cell[0].text
                #grab the year or chamber and hang on to it until it changes
                if header.endswith("REGULAR SESSION"):
                    action_year = header[0:4]
                    action_chamber = chamber #in originating chamber
                elif header.endswith("SENATE"):
                    action_chamber = 'upper'
                elif header.endswith("HOUSE"):
                    action_chamber = 'lower'
                elif header.endswith("OTHER THAN LEGISLATIVE ACTION"):
                    action_chamber = 'other'
                elif header.endswith("SPECIAL SESSION"):
                    action_chamber = 'special'
                else:
                    raise Exception, "unexpected header: " + header
                
            date_cell = row.cssselect('td[valign="top"]')
            if len(date_cell) > 0:
                if date_cell[0].text: 
                    action_date = "%s, %s" % (date_cell[0].text, action_year)
                    
            desc_cell = row.cssselect('td[width="100%"]')
            if len(desc_cell) > 0:
                #clip out the links to other stuff
                links = desc_cell[0].cssselect('span.HistoryLink')
                for link in links:
                    desc_cell[0].remove(link)
                action_desc = desc_cell[0].text_content().strip().rstrip('.')

                self.add_action(chamber, session, number, action_chamber, action_desc, action_date)
    
    def scrape_bills(self, chamber, year):
        # Data available from 1969 on
        if int(year) < 1991 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)
        
        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)
    
        #ignoring lower, getting both chambers on upper -- easier to scrape both at once    
        if chamber == "upper":
            self.scrape(year)
            
            
            
if __name__ == '__main__':
    WALegislationScraper().run()
