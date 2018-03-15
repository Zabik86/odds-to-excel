"""
Soccer match results scraping object.
"""

from bs4 import BeautifulSoup
import xlrd

from DbManager import DatabaseManager
import json
import re
from selenium import webdriver
from SoccerMatch import SoccerMatch
import xlwt
from xlutils.copy import copy
import os


class Scraper():

    def __init__(self, league_json, initialize_db):
        """
        Constructor. Launch the web driver browser, initialize the league
        field by parsing the representative JSON file, and connect to the
        database manager.

        Args:
            league_json (str): JSON string of the league to associate with the
                Scraper.
            initialize_db (bool): Should the database be initialized?
        """

        self.browser = webdriver.Chrome("./chromedriver/chromedriver.exe")
        self.league = self.parse_json(league_json)
        self.db_manager = DatabaseManager(initialize_db)

    def parse_json(self, json_str):
        """
        Parse a JSON string into a dict.

        Args:
            json_str (str): JSON string to parse.

        Returns:
            (dict)
        """

        return json.loads(json_str)

    def scrape_all_urls(self, do_verbose_output=False):
        """
        Call the scrape method on every URL in this Scraper's league field, in
        order, then close the browser.

        Args:
            do_verbose_output (bool): True/false do verbose output.
        """

        if do_verbose_output is True:
            output_str = "Start scraping " + self.league["league"] + " of "
            output_str += self.league["area"] + "..."
            print(output_str)

        for url in self.league["urls"]:
            self.scrape_url_for_next_matches(url)
            self.scrape_url(url)
        self.browser.close()

        if do_verbose_output is True:
            print("Done scraping this league.")

    def scrape_url_for_next_matches(self, url):
        # rb = xlrd.open_workbook(r'C:\Users\seryakov.i\PycharmProjects\odds-to-excel\Болванка для чемпионатов.xlsx')
        # rb = xlrd.open_workbook(r'C:\Users\Илья\PycharmProjects\odds-to-excel\Болванка для чемпионатов.xlsx')
        rb = xlrd.open_workbook('Болванка для чемпионатов.xlsx')
        wb = copy(rb)
        ws = wb.get_sheet(0)
        start_row = 3
        schetchik2 = 0

        next_matches_url = url[0: -8]
        self.browser.get(next_matches_url)
        tournament_tbl_next_matches = self.browser.find_element_by_id("tournamentTable")
        tournament_tbl_html_next_matches = tournament_tbl_next_matches.get_attribute("innerHTML")
        tournament_tbl_soup_next_matches = BeautifulSoup(tournament_tbl_html_next_matches, "html.parser")
        significant_rows_next_matches = tournament_tbl_soup_next_matches(self.is_soccer_match_or_date_for_next_matches)
        championat_name = tournament_tbl_soup_next_matches.find(class_="first2 tl").contents[2].text + " " + \
                          tournament_tbl_soup_next_matches.find(class_="first2 tl").contents[4].text
        current_date_str_for_next_matches = None
        for row_next in significant_rows_next_matches:
            if self.is_date_next_match(row_next) is True:
                if current_date_str_for_next_matches != None and current_date_str_for_next_matches != self.get_date(row_next):
                    break
                else:
                    current_date_str_for_next_matches = self.get_date(row_next)
            elif self.is_date_string_supported(current_date_str_for_next_matches) == False:
                # not presently supported
                continue
            else:
                game_datetime_str_next = current_date_str_for_next_matches + " " + self.get_time_next(row_next)
                participants_next = self.get_participants_next(row_next)

                match_url_next = self.get_match_url_next(row_next)
                mw_odds_next = self.get_odds_mw(row_next)

                # match_url_mw_next = 'http://www.oddsportal.com' + match_url_next + '#1X2;2'
                # self.browser.get(match_url_mw_next)
                # tournament_tbl_match_next = self.browser.find_element_by_id("odds-data-table")
                # tournament_tbl_html_match_next = tournament_tbl_match_next.get_attribute("innerHTML")
                # tournament_tbl_soup_match_next = BeautifulSoup(tournament_tbl_html_match_next, "html.parser")
                # mw_odds_next = self.get_odds_mw(tournament_tbl_soup_match_next.find(class_="aver"))
                # self.browser.back()

                match_url_ttlg_next = 'http://www.oddsportal.com' + match_url_next + '#over-under;2'
                self.browser.get(match_url_ttlg_next)
                tournament_tbl_match_ttlg_next = self.browser.find_element_by_id("odds-data-table")
                tournament_tbl_html_match_ttlg_next = tournament_tbl_match_ttlg_next.get_attribute("innerHTML")
                tournament_tbl_soup_match_ttlg_next = BeautifulSoup(tournament_tbl_html_match_ttlg_next, "html.parser")
                total_strings_next = tournament_tbl_soup_match_ttlg_next.find_all(class_="table-container")

                for string in total_strings_next:
                    ksdjfh = string.contents[0].contents[0].string
                    if string.contents[0].contents[0].string == 'Over/Under +2.5 ':
                        ttlg_odds_next = self.get_odds_ttlg(
                            string.find_all(class_={"avg chunk-odd nowrp", "avg chunk-odd-uk nowrp"}))

                ws.write(schetchik2 + start_row, 20, game_datetime_str_next)
                ws.write(schetchik2 + start_row, 21, participants_next[0])
                ws.write(schetchik2 + start_row, 22, participants_next[1])
                ws.write(schetchik2 + start_row, 23, mw_odds_next[0])
                ws.write(schetchik2 + start_row, 24, mw_odds_next[1])
                ws.write(schetchik2 + start_row, 25, mw_odds_next[2])
                ws.write(schetchik2 + start_row, 26, 2.5)
                ws.write(schetchik2 + start_row, 27, ttlg_odds_next[0])
                ws.write(schetchik2 + start_row, 28, ttlg_odds_next[1])
                schetchik2 += 1
                wb.save(championat_name + ".xls")

    def scrape_url(self, url):
        """
        Scrape the data for every match on a given URL and insert each into the
        database.

        Args:
            url (str): URL to scrape data from.
        """
        # rb = xlrd.open_workbook(r'C:\Users\seryakov.i\PycharmProjects\odds-to-excel\Болванка для чемпионатов.xlsx')
        # rb = xlrd.open_workbook(r'C:\Users\Илья\PycharmProjects\odds-to-excel\Болванка для чемпионатов.xlsx')


        self.browser.get(url)
        tournament_urls_number = (int)(self.browser.find_element_by_id("pagination").text[-4])
        schetchik = 0
        for i in range((tournament_urls_number)):
            if i != 0:
                url1 = url + '#/page/' + str(i + 1) + '/'
            else:
                url1 = url

            self.browser.get(url1)
            tournament_tbl = self.browser.find_element_by_id("tournamentTable")
            tournament_tbl_html = tournament_tbl.get_attribute("innerHTML")
            tournament_tbl_soup = BeautifulSoup(tournament_tbl_html, "html.parser")
            significant_rows = tournament_tbl_soup(self.is_soccer_match_or_date)
            championat_name = tournament_tbl_soup.find(class_="first2 tl").contents[2].text + " " + tournament_tbl_soup.find(class_="first2 tl").contents[4].text
            current_date_str = None

            rb = xlrd.open_workbook(championat_name + '.xls')
            wb = copy(rb)
            ws = wb.get_sheet(0)
            start_row = 3

            for row in significant_rows:
                if self.is_date(row) is True:
                    current_date_str = self.get_date(row)
                elif self.is_date_string_supported(current_date_str) == False:
                    # not presently supported
                    continue
                else:
                    # is a soccer match
                    participants = self.get_participants(row)
                    scores = self.get_scores(row)

                    mw_odds = self.get_odds_mw(row)

                    match_url = self.get_match_url(row)
                    # match_url_mw = 'http://www.oddsportal.com' + match_url + '#1X2;2'
                    # self.browser.get(match_url_mw)
                    # tournament_tbl_match = self.browser.find_element_by_id("odds-data-table")
                    # tournament_tbl_html_match = tournament_tbl_match.get_attribute("innerHTML")
                    # tournament_tbl_soup_match = BeautifulSoup(tournament_tbl_html_match, "html.parser")
                    # mw_odds = self.get_odds_mw(tournament_tbl_soup_match.find(class_="aver"))
                    # self.browser.back()

                    match_url_ttlg = 'http://www.oddsportal.com' + match_url + '#over-under;2'
                    self.browser.get(match_url_ttlg)
                    tournament_tbl_match_ttlg = self.browser.find_element_by_id("odds-data-table")
                    tournament_tbl_html_match_ttlg = tournament_tbl_match_ttlg.get_attribute("innerHTML")
                    tournament_tbl_soup_match_ttlg = BeautifulSoup(tournament_tbl_html_match_ttlg, "html.parser")
                    total_strings = tournament_tbl_soup_match_ttlg.find_all(class_="table-container")

                    for string in total_strings:
                        ksdjfh = string.contents[0].contents[0].string
                        if string.contents[0].contents[0].string == 'Over/Under +2.5 ':
                            ttlg_odds = self.get_odds_ttlg(string.find_all(class_= {"avg chunk-odd nowrp", "avg chunk-odd-uk nowrp"}))

                    tournament_tbl_match_res = self.browser.find_element_by_id("col-content")
                    tournament_tbl_html_match_res = tournament_tbl_match_res.get_attribute("innerHTML")
                    tournament_tbl_soup_match_res = BeautifulSoup(tournament_tbl_html_match_res, "html.parser")
                    result_first_period = self.get_result(tournament_tbl_soup_match_res.find(class_="result"))

                    game_datetime_str = current_date_str + " " + self.get_time(row)

                    ws.write(schetchik + start_row, 1, game_datetime_str)
                    ws.write(schetchik + start_row, 2, participants[0])
                    ws.write(schetchik + start_row, 3, participants[1])
                    ws.write(schetchik + start_row, 4, scores[0])
                    ws.write(schetchik + start_row, 5, scores[1])
                    ws.write(schetchik + start_row, 6, result_first_period[0])
                    ws.write(schetchik + start_row, 7, result_first_period[1])
                    ws.write(schetchik + start_row, 8, mw_odds[0])
                    ws.write(schetchik + start_row, 9, mw_odds[1])
                    ws.write(schetchik + start_row, 10, mw_odds[2])
                    ws.write(schetchik + start_row, 11, 2.5)
                    ws.write(schetchik + start_row, 12, ttlg_odds[0])
                    ws.write(schetchik + start_row, 13, ttlg_odds[1])
                    schetchik += 1
                    file = championat_name + ".xls"
                    wb.save(file)
        os.system(
            r'C:\Users\seryakov.i\PycharmProjects\odds-to-excel\prem\ConsoleApplication1.exe  file')


    def is_soccer_match_or_date(self, tag):
        """
        Determine whether a provided HTML tag is a row for a soccer match or
        date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """

        if tag.name != "tr":
            return False
        if "center" in tag["class"] and "nob-border" in tag["class"]:
            return True
        if "deactivate" in tag["class"] and tag.has_attr("xeid"):
            return True
        return False

    def is_soccer_match_or_date_for_next_matches(self, tag):

        if tag.name != "tr":
            return False
        if tag.has_attr("xeid"):
            return True
        if "center" in tag["class"] and "nob-border" in tag["class"]:
            return True
        return False

    def is_date_next_match(self, tag):
        """
        Determine whether a provided HTML tag is a row for a date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """
        if tag.has_attr("xeid"):
            return False
        else:
            return "center" in tag["class"] and "nob-border" in tag["class"]

    def is_date(self, tag):
        """
        Determine whether a provided HTML tag is a row for a date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """
        return "center" in tag["class"] and "nob-border" in tag["class"]

    def is_date_string_supported(self, date_string):
        """
        Determine whether a given date string is currently supported by this
        software's parsing capabilities.

        Args:
            date_string (str): Date string to assess.

        Returns:
            (bool)
        """

        if date_string is None:
            return False
        elif "Today" in date_string:
            return False
        elif "Yesterday" in date_string:
            return False
        elif "Qualification" in date_string:
            return False
        elif "Promotion" in date_string:
            return False
        return True

    def get_date(self, tag):
        """
        Extract the date from an HTML tag for a date row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) Extracted date string.
        """

        this_date = tag.find(class_="datet").string
        if "Today" in this_date:
            return "Today"
        elif this_date.endswith(" - Play Offs"):
            this_date = this_date[:-12]
        return this_date

    def get_time_next(self, tag):
        return tag.find(class_="table-time").string

    def get_time(self, tag):
        """
        Extract the time from an HTML tag for a soccer match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) Extracted time.
        """
        
        return tag.find(class_="datet").string

    def get_match_url(self, tag):
        parsed_strings = tag.find(class_="table-participant").contents[0].attrs['href']
        return parsed_strings

    def get_match_url_next(self, tag):
        if (len(tag.contents[1].contents) > 2):
            parsed_strings = tag.find(class_="table-participant").contents[2].attrs['href']
        else:
            parsed_strings = tag.find(class_="table-participant").contents[0].attrs['href']
        return parsed_strings

    def get_participants_next(self, tag):
        if (len(tag.contents[1].contents) > 2):
            parsed_strings = tag.contents[1].contents[2].text.split(" - ")
        else:
            parsed_strings = tag.contents[1].contents[0].text.split(" - ")
        participants = []
        participants.append(parsed_strings[0])
        participants.append(parsed_strings[-1])
        return participants

    def get_participants(self, tag):
        """
        Extract the match's participants from an HTML tag for a soccer match
        row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match participants.
        """
        
        parsed_strings = tag.find(class_="table-participant").text.split(" - ")
        participants = []
        participants.append(parsed_strings[0])
        participants.append(parsed_strings[-1])
        return participants

    def get_scores(self, tag):
        """
        Extract the scores for each team from an HTML tag for a soccer match
        row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match scores.
        """

        score_str = tag.find(class_="table-score").string
        if self.is_invalid_game_from_score_string(score_str):
            return [-1,-1]
        non_decimal = re.compile(r"[^\d]+")
        score_str = non_decimal.sub(" ", score_str)
        scores = [int(s) for s in score_str.split()]
        return scores

    def get_odds_mw(self, tag):
        odds_cells = tag.find_all(class_="odds-nowrp")
        odds = []
        for cell in odds_cells:
            if "/" in cell.text:
                k = cell.text.split('/')
                odds.append(float(1+(float)(k[0])/(float)(k[1])))
            else:
                odds.append(cell.text)
        return odds

    def get_result(self, tag):
        result = []
        res = tag.text
        result.append((int)(res[18]))
        result.append((int)(res[20]))
        return result

    def get_odds_ttlg(self, tag):
        odds = []
        for cell in tag:
            if "/" in cell.text:
                k = cell.text.split('/')
                odds.append(float(1+(float)(k[0])/(float)(k[1])))
            else:
                odds.append(cell.text)
        if len(odds) == 0:
            odds.append(-1)
            odds.append(-1)
        return odds

    def get_odds(self, tag):
        """
        Extract the betting odds for a match from an HTML tag for a soccer
        match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match odds.
        """

        odds_cells = tag.find_all(class_="odds-nowrp")
        odds = []
        for cell in odds_cells:
            odds.append(cell.text)
        return odds

    def is_invalid_game_from_score_string(self, score_str):
        """
        Assess, from the score string extracted from a soccer match row,
        whether a game actually paid out one of the bet outcomes.

        Args:
            score_str (str): Score string to assess.

        Returns:
            (bool)
        """

        if score_str == "postp.":
            return True
        elif score_str == "canc.":
            return True
        return False
