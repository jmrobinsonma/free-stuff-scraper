import os
import sys
import smtplib
from bs4 import BeautifulSoup
from requests import get
from sqlalchemy import create_engine, exc, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from email.message import EmailMessage

Base = declarative_base()
class Posts(Base):

    __tablename__ = "posts"

    timing = Column(String(120), unique=False, nullable=False, primary_key=True)
    title_text = Column(String(120), unique=False, nullable=False)
    price = Column(String(120), unique=False, nullable=False)
    link = Column(String(120), unique=False, nullable=False)

class DealScraper:

	def __init__(self,urls,name,):
		self.urls = urls
		self.name = name
		self.session = False
		self.instance_filename = ""
		self.instance_responses = ()
		self.instance_results = ()
		self.new_results_titles = []
		self.new_results_links = []
		self.new_results = ()
		self.post_timing = []
		self.post_title_texts = []
		self.post_prices = []
		self.post_links = []
		self.num_posts = 0
		self.num_new_results = 0
		self.results_msg = ""
		self.EMAIL_ADDRESS = ""
		self.EMAIL_PASSWORD = ""

	def get_results(self):

		try:
			for url in self.urls:
				response = get(url)
				soup = BeautifulSoup(response.text,'html.parser')
				posts = soup.find_all('li',class_='result-row')

				for post in posts:
					post_title = post.find('p', class_='result-info')
					post_link = post_title.a['href']
					region = bool(post_link.split('/')[2].split('.')[0]=='westernmass')

					if region:
						self.num_posts += 1

						post_title_text = post_title.text.split('\n')[5]
						self.post_title_texts.append(post_title_text)

						post_link = post_title.a['href']
						self.post_links.append(post_link)

						post_price = post_title.find('span',class_='result-price').text
						self.post_prices.append(post_price)

						post_datetime = post.find('time', class_= 'result-date')['datetime']
						self.post_timing.append(post_datetime)
		except Exception as e:
			print(f"{e}")
		if self.num_posts:
			self.instance_results = (self.post_timing, self.post_title_texts, self.post_prices, self.post_links, self.num_posts)
			return self.instance_results
		else:
			sys.exit()

	def db_connect(self):
		try:
			engine = create_engine(f'sqlite:////home/jrob/db_api/{self.name}.db')  #echo=True for output to console
			Base.metadata.create_all(bind=engine)
			Session = sessionmaker(bind=engine)
			self.session = Session()
		except Exception as e:
			print(f"\nThere was a problem connecting to the database!\n--> {e}")

	def db_update(self, instance_results, session):
		post_timing, post_title_texts, post_prices, post_links, num_posts = instance_results

		duplicates = 0
		try:
			for i in range(len(post_links)):
				try:
					post = Posts()
					post.timing = post_timing[i]
					post.title_text = post_title_texts[i]
					self.new_results_titles.append(post_title_texts[i])
					post.price = post_prices[i]
					post.link = post_links[i]
					self.new_results_links.append(post_links[i])
					self.session.add(post)
					self.session.commit()
				except exc.IntegrityError as e:
					duplicates += 1
					self.new_results_titles.pop()
					self.new_results_links.pop()
					self.session.rollback()
			self.new_results = (self.new_results_titles, self.new_results_links)
			self.num_new_results = num_posts - duplicates
			return self.num_new_results
		except Exception as e:
			print(f"\nThere was a problem updating the database!\n--> {e}")

	def show_num_results(self, num_new_results, instance_results):
		post_timing, post_title_texts, post_prices, post_links, num_posts = instance_results

		print(f"\n{self.num_new_results} New results\n")
		for result in range(num_posts):
			print(f"Result {result + 1}\n{post_title_texts[result]}\n{post_prices[result]}\n{post_links[result]}\n")

	def db_close(self, session):
		self.session.close()

	def create_msg(self, new_results):
		titles, links = new_results

		for i, post in enumerate(titles):
			result = f"""

Result {i+1}
	{titles[i]}
	{links[i]}
			"""
			self.results_msg = self.results_msg + result
		return self.results_msg


	def get_cred(self):

		try:
			self.EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
			if not self.EMAIL_ADDRESS:
				print("\nThere was a problem obtaining environment variable for username and an email will not be sent!")
				sys.exit()
		except Exception as e:
			print(f"\nThere was a problem obtaining environment variable for your username!")
		try:
			self.EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')
			if not self.EMAIL_PASSWORD:
				print("\nThere was a problem obtaining environment variable for your password and an email will not be sent!")
				sys.exit()
		except Exception as e:
			print(f"\nThere was a problem obtaining environment variable for your password!\n--> {e}")
		return self.EMAIL_ADDRESS, self.EMAIL_PASSWORD


	def send_mail(self, EMAIL_ADDRESS, EMAIL_PASSWORD, results_msg):

		msg = EmailMessage()
		msg['Subject'] = f"{self.name}"
		msg['From'] = self.EMAIL_ADDRESS
		msg['to'] = self.EMAIL_ADDRESS
		msg.set_content(self.results_msg)

		try:
			with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
			    smtp.login(self.EMAIL_ADDRESS, self.EMAIL_PASSWORD)
			    smtp.send_message(msg)
			print("Email Sent")
		except Exception as e:
			print(f"\nThere was a problem while attempting to send your email!\n--> {e}")


urls = ["https://westernmass.craigslist.org/search/zip?hasPic=1&postedToday=1"]

def main():

	find_freestuff = DealScraper(urls, "free-stuff")
	find_freestuff.get_results()
	find_freestuff.db_connect()
	find_freestuff.db_update(find_freestuff.instance_results, find_freestuff.session)
	find_freestuff.show_num_results(find_freestuff.num_new_results, find_freestuff.instance_results)
	if find_freestuff.num_new_results:
		find_freestuff.db_close(find_freestuff.session)
		EMAIL_ADDRESS,EMAIL_PASSWORD = (find_freestuff.get_cred())
		find_freestuff.create_msg(find_freestuff.new_results)
		find_freestuff.send_mail(EMAIL_ADDRESS,EMAIL_PASSWORD, find_freestuff.results_msg)
	else:
		find_freestuff.db_close(find_freestuff.session)
	sys.exit()

if __name__ == '__main__':
	main()
