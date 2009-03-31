#!/usr/bin/env python
import urllib2
import re
import datetime as dt
#beautiful soup dies on the bill summary page, switching to lxml
#from BeautifulSoup import BeautifulSoup
from lxml.html import parse

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class WALegislationScraper(LegislationScraper):

    state = 'wa'

    def scrape(self, year):
      
        # get bills by topic search page -- gives a list of bill IDs per year
        bills_url = 'http://apps.leg.wa.gov/billsbytopic/default.aspx?year=%s' % (year)
        print bills_url
        bills = parse(bills_url).getroot()
        for option in bills.cssselect('select#ucDefault_talCriteria option'):
            number = option.text
            
            #TODO: figure out what to do w/ three digit bills
            if len(number) > 3:
            
                #get bill summary
                summary_url = 'http://dlr.leg.wa.gov/billsummary/default.aspx?Bill=%s&year=%s' % (number, year)
                print summary_url
                summary = parse(summary_url).getroot()
                
                #TODO: this doesn't work for 2005
                
                if summary.cssselect('span#ctl00_contentRegion_lblShortBillID')[0].text.startswith('HB'):
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
                           
                #TODO: amendments -- new thing? -- isamendment field on version
                #TODO: new csv, not in core, fiscal_notes
                #TODO: extra field on action for the bill version link
                
                #the dates are incomplete on the web page we're scraping
                #so we must match the page w/ the rss feed to get all the goods
                #the rss feed doesn't have the chamber for the actions, so we scrape that from the page
                page_actions = []
                action_chamber = chamber #start with the originating chamber
                for x in summary.cssselect('tr#ctl00_contentRegion_trPlaceHolder>td>table>tr'):
                    y = x.cssselect('td[colspan="3"] b')
                    if len(y) > 0:
                        header = y[0].text
                        #grab the action chamber and hang on to it until it changes
                        #xTODO: find an example where it changes and test:
                        #this seems to work! http://dlr.leg.wa.gov/billsummary/default.aspx?year=1995&bill=1009
                        #TODO: but there's another thing, OTHER LEGISLATIVE ACTION that we need to account for
                        
                        if header.endswith("SENATE"):
                            action_chamber = 'upper'
                        if header.endswith("HOUSE"):
                            action_chamber = 'lower'
                    z = x.cssselect('td[width="100%"]')
                    if len(z) > 0:
                        #clip out the links to other stuff
                        links = z[0].cssselect('span.HistoryLink')
                        for link in links:
                            z[0].remove(link)
                        act = z[0].text_content().strip().rstrip('.')
                        page_actions.append([act,action_chamber])

                #reverse to match up w/ order of feed
                page_actions.reverse()

                actions_feed_url = 'http://apps.leg.wa.gov/billinfo/summaryrss.aspx?year=%s&bill=%s' % (year, number)
                print actions_feed_url
                actions_feed = parse(actions_feed_url).getroot()
                actions = actions_feed.cssselect('item title')
                i = 0
                for action in actions:
                    action_split = action.text.split(' - ')
                    action_date = action_split[1]
                    action_desc = action_split[2]
                    action_chamber = page_actions[i][1]
                    i += 1
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
