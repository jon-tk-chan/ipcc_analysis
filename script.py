from bs4 import BeautifulSoup
import pandas as pd
import requests
import re
import json
from nltk.corpus import cmudict

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer 
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

ipcc_url = "https://www.ipcc.ch/sr15/chapter/spm/"
output_folder = "data/"

#SCRAPING FUNCTIONS
def get_soup(url): 
    """returns the BeautifulSoup object from a given url"""
    html = requests.get(url).text

    soup = BeautifulSoup(html, 'html.parser')
    
    return soup

def get_raw_dict(soup, pattern):
    """returns the paragraphs from the IPCC BeautifulSoup using the pattern regex pattern
    Also returns the full text as a text string"""
    
    prog = re.compile(pattern)
    ind = 0
    full_text = ""

    raw_dict = {}
    for para in soup.find_all('p', href=False):

        para_text = para.get_text()


        result = prog.match(para_text)
        if result:
            ind += 1
            full = result.group(0) #FULL MATCHING TEXT
            para_id = result.group(1) #paragraph letter/number
            content = result.group(2) #content of text
            tags_string = result.group(3) #tags AS A STRING

            #create a new dict for this entry, then save each component in nested dict
            raw_dict[str(ind)] = {
                "PARA_ID": para_id,
                "RAW_TEXT": content,
                "TAGS": tags_string

            }
            
            full_text += content

    return raw_dict, full_text

#READING DIFFICULTY FUNCTIONS
#READING FORMULAS FROM: https://medium.com/analytics-vidhya/visualising-text-complexity-with-readability-formulas-c86474efc730
#ARI: https://readabilityformulas.com/automated-readability-index.php
#Flesch Reading age, ease: https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests
def num_syllables(word, word_dict):
    """return num of syllables in word using either CMU dict or number of vowels"""
    
    syl_count = 0
    vowels = {"a","e","i","o","u","y"}
    
    if word in word_dict:
        pronounciation = word_dict[word][0]
        pronounciation_str = ''.join(pronounciation)
        
        digit_count = 0
        
        for letter in pronounciation_str:
            if letter.isdigit():
                digit_count += 1
        syl_count = digit_count
    else:
        vowel_count = 0
        for char in word.lower():
            if char in vowels:
                vowel_count += 1
        syl_count = vowel_count
    return syl_count

def flesch_reading_ease(text):
    """return reading ease for a full text string
    
    90-100 understood by 11 year old student
    60-10 easily understood by 13-15 year old student
    0-30 best understood by university graduates"""
    
    all_sents = text.split(". ")
    
    for sent in all_sents:
        sent_list = sent.split()
        for word in sent_list:
            if not word.isalpha():
                sent_list.remove(word)
        syl_count = 0
        total_sent = 1
        total_words = 0
        
        if len(sent_list) == 0:
            return None
        else:
            for word in sent_list:
                total_words += 1
                syl_count += num_syllables(word, p_dict)
                
        reading_score = 206.835 - 1.015*(total_words/total_sent) - 84.6*(syl_count/total_words)
        
        return reading_score   

def SMOG(text):
    """return the smog grade """
    all_sents = text.split(". ")
    
    num_polysyl = 0 
    num_words = 0
    num_sents = len(all_sents)
    for sent in all_sents:
        sent_list = sent.split()
        for word in sent_list:
            num_words += 1
            syl_count = num_syllables(word, p_dict)
            if syl_count >= 3:
                num_polysyl += 1
    smog_grade = 1.0430*((num_polysyl*(30/num_sents))**0.5 + 3.1291)
    return smog_grade

def flesch_kincaid_reading_age(text):
    
    """reading age 
    https://medium.com/analytics-vidhya/visualising-text-complexity-with-readability-formulas-c86474efc730"""
    
    all_sents = text.split(". ")
    
    total_words = 0
    total_sents = len(all_sents)
    total_syllables = 0
    
    for sent in all_sents:
        sent_list = sent.split()
        for word in sent_list:
            total_words += 1
            total_syllables += num_syllables(word, p_dict)
            
    fkra = 0.39*(total_words/total_sents) + 11.8*(total_syllables/total_words) - 15.59
    
    return fkra if fkra > 0 else 0

def ARI(text):
    """returns the Automated readability index for a given text string"""
    
    all_sents = text.split(". ")
    
    num_sents = len(all_sents)
    num_char = 0
    num_words = 0
    
    for sent in all_sents:
        sent_list = sent.split()
        for word in sent_list:
            num_char += len(word)
            num_words += 1
    ari_score = 4.71*(num_char/num_words) + 0.5*(num_words/num_sents) - 21.43

    return ari_score

def word_count(text):
    """return the word count for a given text string"""
    
    all_words = text.split()
    return len(all_words)

def reading_time(text):
    """Return the number of minutes for reading a given text (assuming 250 word/min)"""
    return word_count(text) / 250

#TEXT SUMMARIZE FUNCTIONS

def lsa_summarize(input_dict):
    """Return the summarized text given the raw_dict from get_raw_dict()"""
    
    summarizer_lsa = LsaSummarizer()
    summarizer_lsa = LsaSummarizer(Stemmer("english"))
    summarizer_lsa.stop_words = get_stop_words("english")
    lsa_fulltext = ""
    
    for key, value in input_dict.items():
        text = value["RAW_TEXT"]
        parser = PlaintextParser.from_string(text,Tokenizer("english"))
        summary = summarizer_lsa(parser.document, 1)[0]
        lsa_fulltext += str(summary) + " "
    return lsa_fulltext
    
def lexrank_summarize(input_dict):
    """Return the summarized text given the raw_dict from get_raw_dict()"""
    summarizer_lr = LexRankSummarizer()
    lr_fulltext = ""
    
    for key, value in input_dict.items():
        text = value["RAW_TEXT"]
        parser = PlaintextParser.from_string(text,Tokenizer("english"))
        summary = summarizer_lr(parser.document, 1)[0]
        lr_fulltext += str(summary) + " "
    return lr_fulltext

#RESULTS FUNCTIONS
def get_results_df(raw_str, lsa_str, lr_str):
    """return a dataframe of all reading metric values for given input text strings
    
    raw_str: original text 
    lsa_str: text summarized using LsaSummarizer
    lr_str: text summarized using LexRankSummarizer
    """
    columns = ["word count", "reading time (min)", "ARI", "SMOG", "Flesch Kincaid Reading Ease", "Flesch Kincaid Reading Age"]
    fn_list = [word_count, reading_time, ARI, SMOG, flesch_reading_ease, flesch_kincaid_reading_age]
    results_dict = {
        "Raw": {},
        "LSA": {},
        "LexRank": {}

    }

    for i, fn in enumerate(fn_list):
        results_dict["Raw"][columns[i]] = fn(raw_str)
        results_dict["LSA"][columns[i]] = fn(lsa_str)
        results_dict["LexRank"][columns[i]] = fn(lr_str)


    results_df = pd.DataFrame.from_dict(results_dict, orient = "index",
                                       columns=columns).round(2)

    return results_df

def get_baseline_df(results):
    """return a baseline comparison dataframe given a results dataframe
    
    Assume baseline reading level is approximately 7th grade (12-14 year old):
    https://centerforplainlanguage.org/what-is-readability/#:~:text=Your%20audience's%20reading%20age%20is%20lower%20than%20you%20think&text=U.S.%20illiteracy%20statistics%20from%20the,12%20to%2014%20years%20old).
    
    """
    
    baseline_vals = [7.0, 7.0, 80.00, 7.0]
    baseline_df = results.iloc[1:, 2:]
    baseline_df.loc["baseline"] = baseline_vals
    
    return baseline_df

#MAIN
def main():
    soup = get_soup(ipcc_url)
    pattern = "^( ?[A-Z]\.[1-9\.]+) *([^{}]*)(.*)"

    raw_dict, raw_text = get_raw_dict(soup, pattern)
    lsa_text = lsa_summarize(raw_dict)
    lr_text = lexrank_summarize(raw_dict)


    results_df = get_results_df(raw_text, lsa_text, lr_text)
    baseline_df = get_baseline_df(results_df)

    results_df.to_csv(path_or_buf="results/results.csv")
    print("FILE CREATED: ", "results/results.csv")
    baseline_df.to_csv(path_or_buf="results/baseline_comparison.csv")
    print("FILE CREATED: ", "results/baseline_comparison.csv")
    
    print("OUTPUTS WRITTEN INTO FOLDER: results")

if __name__ == "__main__":
    p_dict = cmudict.dict()
    main()