import rich, rich.console, rich.panel, rich.markdown, rich.live, rich.text, rich.prompt
console = rich.console.Console()

with console.status("Ladataan..."):
	console.log("Ladataan standardikirjastoja...")
	import time
	from typing import Any, Callable

	console.log("Ladataan openai...")
	import openai
	import openai.error

	console.log("Ladataan kääntäjä...")
	import translation

THRESHOLD = 0.5
PROMPT = """Tehtäväsi on kirjoittaa eroottinen runo. Runon on oltava kiihottava ja vihjaileva. Käytä ronskia kieltä vain, jos runon aiheessakin käytetään ronskia kieltä.

Runon aihe: {}

Runon teksti:"""

def safe_input(prompt: str = "", print_report: Callable[[str | None, float], None] | None = None) -> str:
	while True:
		text = input(prompt)
		if not check_string(text, print_report):
			break
	
	return text

TRANSLATIONS = {
	"hate": "vihapuhe",
	"hate/threatening": "vihapuhe/uhkaus",
	"self-harm": "itsetuhoisuus",
	"sexual": "seksuaalisuus",
	"sexual/minors": "seksuaalisuus/alaikäiset",
	"violence": "väkivalta",
	"violence/graphic": "väkivalta/graafinen",
}

def check_string(text: str, print_report: Callable[[str | None, float], None] | None = None, translate=True) -> bool:
	global category_scores

	if translate:
		with console.status("Käännetään..."):
			english = translation.translate(text)
			console.print(f"Käännös englanniksi: [i]{english}")
		
		with console.status("Moderoidaan..."):
			response1: Any = openai.Moderation.create(text)
			response2: Any = openai.Moderation.create(english)
		
		#print(response["results"][0]["category_scores"])
		
		category_scores1 = response1["results"][0]["category_scores"]
		category_scores2 = response2["results"][0]["category_scores"]

		category_scores = {key: max(category_scores1[key], category_scores2[key]) for key in category_scores1}
	
	else:
		with console.status("Moderoidaan..."):
			response: Any = openai.Moderation.create(text)
		
		category_scores = response["results"][0]["category_scores"]

	for category in ["hate", "sexual", "self-harm", "violence"]:
		name = TRANSLATIONS[category].upper()
		value = category_scores[category]
		percent = f"{100*value: >5.2f}".replace(".", ",")
		color = "green" if value < 0.1 else \
			"yellow" if value < 0.5 else\
			"red"
		console.print(f"[bold]{name: >14}: [{color}]{percent} %", end=" " if category in {"hate", "self-harm"} else "\n")

	argmax = None
	m = 0
	for category, value in category_scores.items():
		if value > m:
			argmax = category
			m = value
	
	if m >= THRESHOLD:
	
		if print_report:
			print_report(argmax, m)
		
		return True
	
	return False

def make_reporter(message):
	def print_report(reason, percent):
		reason = TRANSLATIONS[reason]
		percent = f"{100*percent:.2f}".replace(".", ",")
		rich.print(rich.panel.Panel.fit(f"[bold red]{message}[/bold red]\nSYY: [i]{reason}[/i] ({percent} %)"))
	
	return print_report

def generate(prompt: str):
	while True:
		try:
			with console.status("Odotetaan palvelinta..."):
				response: Any = openai.Completion.create(
					model="text-davinci-003",
					prompt=prompt,
					temperature=0.7,
					max_tokens=1000,
					stream=True,
					request_timeout=5,
				)
			
				yield "ok"
			break
		except openai.error.Timeout:
			console.log("Timeout. Odotetaan 5 sekuntia...")
			with console.status("Odotetaan..."):
				time.sleep(5)
		except openai.error.RateLimitError:
			console.log("RateLimitError. Odotetaan 5 sekuntia...")
			with console.status("Odotetaan..."):
				time.sleep(5)
			
	for response in response:
		yield response["choices"][0]["text"]

	#generated_text = response["choices"][0]["text"]


def add_newlines(line: str):
	lines = []
	while len(line) >= 32:
		left = line
		right = ""
		while len(left) >= 32 and " " in left:
			i = left.rindex(" ")
			right = left[i:] + right
			left = left[:i]
		
		if right == "":
			break
		
		lines.append(left)
		line = right
	
	return "\n".join(lines + [line])


def printer_print(text: str, **kwargs):
	for line in text.splitlines():
		line = add_newlines(line)
		print(line, **kwargs)


def printer_print_columns(text1: str, text2: str, **kwargs):
	spaces = " "*(31-len(text1)-len(text2))
	printer_print(f"{text1}{spaces}{text2}", **kwargs)


n = 1
while True:
	import os
	os.system("clear")

	console.rule("Tekoälyn rakkausrunot")
	user_input = safe_input("Anna runolle aihe tai kirjoitusohjeet: ", make_reporter("SYÖTTEESI ON HYLÄTTY."))
	generation = ""
	text = rich.text.Text()
	panel = rich.panel.Panel.fit(text)
	generator = generate(PROMPT.format(user_input))
	next(generator)
	try:
		with rich.live.Live(panel, refresh_per_second=8):
			for token in generator:
				if generation == "":
					token = token.lstrip()
				generation += token
				text.append(token)
		
	except:
		console.print("[bold red]\\[Virhe generoinnin aikana]")

	#if not check_string(generation, make_reporter("TULOS HYLÄTTY."), translate=False):
	#	rich.print(rich.panel.Panel.fit(f"[bold green]TULOS HYVÄKSYTTY.[/bold green]"))

	if rich.prompt.Confirm.ask("Tulostetaanko runo?"):
		with open("/tmp/tulostin", "w") as f:
			printer_print_columns("HEUREKA", "H18-ilta", file=f)
			printer_print_columns("Runo nro", str(n), file=f)
			printer_print_columns("Päivämäärä", "10.2.2023", file=f)
			printer_print("\n", file=f)

			printer_print(user_input, file=f)
			printer_print("\n", file=f)
			printer_print(generation, file=f)
			printer_print("\n", file=f)
			for category in ["hate", "sexual", "self-harm", "violence"]:
				name = TRANSLATIONS[category].upper()
				value = category_scores[category]
				percent = f"{100*value: >5.2f}".replace(".", ",")
				printer_print(f"{name: >13}: {percent} %", file=f)
	
	input("Paina enteriä jatkaaksesi")
	n += 1