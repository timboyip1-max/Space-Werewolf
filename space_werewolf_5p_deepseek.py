"""
space_werewolf_5p_deepseek.py
Space Werewolf (5-player version): Fixed fixed impostor roles and impostor guaranteed loss issues, optimized balance
Core Rule: 95% vote for the highest suspicion player, 5% random vote (simulate minimal misjudgment probability)
"""
import os
import random
import json
import traceback
from typing import Dict, Optional, List, Tuple

# ---------------------- 1. OpenAI Client Import Handling ----------------------
try:
    from openai import OpenAI
except ImportError:
    print("❌ openai library not installed, please run: pip install openai>=1.0.0")
    OpenAI = None

# ---------------------- 2. Integrated Configuration Class (Env Loading + API Config) ----------------------
class Config:
    # Env file configuration
    ENV_FILE_NAME = "DEEPSEEK_API_KEY.env"
    
    # API Configuration (loaded from env or use defaults)
    DEEPSEEK_BASE_URL = ""
    DEEPSEEK_API_KEY = ""
    MODEL_NAME = ""

    @classmethod
    def load_env(cls):
        """Load environment variables from .env file (with fallback for missing python-dotenv)"""
        # Try to load with python-dotenv first
        try:
            from dotenv import load_dotenv
            env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cls.ENV_FILE_NAME)
            load_dotenv(dotenv_path=env_file_path, override=True)
            print(f"✅ Environment file loaded: {env_file_path}")
        except ImportError:
            print("⚠ python-dotenv not installed, using manual env file parsing")
            cls._manual_parse_env()
        
        # Initialize config values (env first, then defaults)
        cls.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        cls.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        cls.MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    @classmethod
    def _manual_parse_env(cls):
        """Fallback: manually parse .env file if python-dotenv is missing"""
        env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cls.ENV_FILE_NAME)
        if not os.path.exists(env_file_path):
            print(f"❌ Environment file not found: {env_file_path}")
            return
        
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    print(f"⚠ Line {line_num} format error: {line}")
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        print(f"✅ Environment file parsed manually: {env_file_path}")

    @classmethod
    def validate(cls):
        """Validate API configuration"""
        if not cls.DEEPSEEK_API_KEY:
            print("⚠ API Key not configured, automatically enabling local simulation mode (using preset dialogues)")
        if not cls.DEEPSEEK_BASE_URL.endswith("/v1"):
            print(f"⚠ Base URL is recommended to end with /v1, current: {cls.DEEPSEEK_BASE_URL}")

# ---------------------- 3. Game Core Configuration (Fixed 5-player version) ----------------------
LOCATIONS = ["Space Ship (5-player version: 3 Crewmates + 2 Impostors)"]

class GameConfig:
    TEMPERATURE = float(os.getenv("SPACE_WEREWOLF_TEMPERATURE", "0.8"))
    MAX_TOKENS = int(os.getenv("SPACE_WEREWOLF_MAX_TOKENS", "150"))
    
    TOTAL_PLAYERS = 5  # Fixed for 5-player version
    ROUNDS_PER_VOTE = 2  # Action report rounds before each voting round
    VOTE_ROUNDS = 2  # Total voting rounds to ensure game conclusion
    SPEECH_LENGTH_MIN = 12
    SPEECH_LENGTH_MAX = 22
    DEBATE_LENGTH_MIN = 25
    DEBATE_LENGTH_MAX = 45
    RANDOM_VOTE_RATE = 0.05  # Increased random vote rate to 5% for more uncertainty
    IMPOSTER_SUSPECT_BIAS = 0.05  # Impostor suspicion bias reduced to 5%

# ---------------------- 4. Advanced AI Client ----------------------
class AdvancedDeepSeekClient:
    def __init__(self):
        self.available = False
        self.client = None
        self.mock_mode = True
        if OpenAI is not None and Config.DEEPSEEK_API_KEY:
            try:
                self.client = OpenAI(
                    api_key=Config.DEEPSEEK_API_KEY,
                    base_url=Config.DEEPSEEK_BASE_URL
                )
                self.client.models.list()
                self.available = True
                self.mock_mode = False
                print("✅ DeepSeek API client initialized successfully (Space Werewolf mode)")
            except Exception as e:
                error_msg = str(e)[:50]
                print(f"⚠ API initialization failed (enabling simulated dialogues): {error_msg}")

    def _filter_speech(self, speech: str, is_imposter: bool, role: str) -> bool:
        speech = speech.strip()
        crew_keywords = {
            "Engineer Kai (Crewmate)": ["repair", "timestamp", "reactor", "oxygen tank"],
            "Communications Officer Lina (Crewmate)": ["monitor", "communication", "interference", "recording"],
            "Navigator Ella (Crewmate)": ["trajectory", "data", "course", "calibration"],
            "Doctor Mark (Crewmate)": ["physical exam", "vital signs", "medical bay", "first-aid kit"],  # New crew role
            "Technician Lucy (Crewmate)": ["circuit", "sensor", "equipment inspection", "repair tools"]  # New crew role
        }
        if not is_imposter and role in crew_keywords:
            has_keyword = any(kw in speech for kw in crew_keywords[role])
            return (GameConfig.SPEECH_LENGTH_MIN <= len(speech) <= GameConfig.SPEECH_LENGTH_MAX) and has_keyword
        imposter_forbid = ["timestamp", "recording", "trajectory log", "wrench position", "raw vital sign data"]
        return (GameConfig.SPEECH_LENGTH_MIN <= len(speech) <= GameConfig.SPEECH_LENGTH_MAX) and not any(kw in speech for kw in imposter_forbid)

    def _filter_debate(self, debate: str) -> bool:
        debate = debate.strip()
        return GameConfig.DEBATE_LENGTH_MIN <= len(debate) <= GameConfig.DEBATE_LENGTH_MAX

    def generate_speech(self, system_prompt: str, round_num: int) -> str:
        user_prompt = f"""
        You are a Space Werewolf player. Action report requirements for Round {round_num}:
        1. Only output an action description of {GameConfig.SPEECH_LENGTH_MIN}-{GameConfig.SPEECH_LENGTH_MAX} characters;
        2. Natural language, like a real player's report;
        3. No explanations, no questions, no revealing impostor identity.
        """
        retry = 3
        while retry > 0:
            try:
                if self.mock_mode:
                    speech = self._mock_speech(system_prompt)
                else:
                    resp = self.client.chat.completions.create(
                        model=Config.MODEL_NAME,
                        messages=[{"role":"system","content": system_prompt}, {"role":"user","content": user_prompt}],
                        temperature=GameConfig.TEMPERATURE,
                        max_tokens=GameConfig.MAX_TOKENS,
                        timeout=20
                    )
                    speech = resp.choices[0].message.content.strip()
                is_imposter = "Impostor" in system_prompt
                role = next((r for r in [
                    "Engineer Kai", "Communications Officer Lina", "Navigator Ella", "Doctor Mark", "Technician Lucy",
                    "Impostor Vic", "Impostor Zoe", "Impostor Jack", "Impostor Lily"
                ] if r in system_prompt), "")
                if self._filter_speech(speech, is_imposter, role):
                    return speech
                retry -= 1
            except Exception as e:
                print(f"⚠ Action report generation failed (retry {retry}): {str(e)[:30]}")
                retry -= 1
        return self._mock_speech(system_prompt)

    def generate_debate(self, system_prompt: str, suspect_target: int) -> str:
        user_prompt = f"""
        You are suspected of being an impostor by Player {suspect_target}. Defense requirements:
        1. Only output a defense of {GameConfig.DEBATE_LENGTH_MIN}-{GameConfig.DEBATE_LENGTH_MAX} characters;
        2. Natural tone (crewmates present evidence, impostors counterattack/shift blame);
        3. Strengthen your own identity.
        """
        retry = 3
        while retry > 0:
            try:
                if self.mock_mode:
                    debate = self._mock_debate(system_prompt, suspect_target)
                else:
                    resp = self.client.chat.completions.create(
                        model=Config.MODEL_NAME,
                        messages=[{"role":"system","content": system_prompt}, {"role":"user","content": user_prompt}],
                        temperature=GameConfig.TEMPERATURE + 0.1,
                        max_tokens=GameConfig.MAX_TOKENS,
                        timeout=20
                    )
                    debate = resp.choices[0].message.content.strip()
                if self._filter_debate(debate):
                    return debate
                retry -= 1
            except Exception as e:
                print(f"⚠ Defense generation failed (retry {retry}): {str(e)[:30]}")
                retry -= 1
        return self._mock_debate(system_prompt, suspect_target)

    def analyze_suspect(self, all_reports: Dict[int, List[str]], all_defenses: Dict[int, str], real_scene: str, imposter_ids: List[int]) -> Dict[int, float]:
        """Added imposter_ids parameter for more accurate analysis"""
        try:
            if self.mock_mode or not self.available:
                return self._mock_suspect_analysis(all_reports, imposter_ids)
            
            report_text = "\n".join([f"Player {pid}: {' | '.join(rp)}" for pid, rp in all_reports.items()])
            defense_text = "\n".join([f"Player {pid}: {df}" for pid, df in all_defenses.items()])
            system_prompt = f"""
            You are a fair referee for Space Werewolf. Analyze each player's impostor suspicion level (0-1) with the following rules:
            1. The real scene is "{real_scene}". Crewmates' speeches contain job-related keywords; impostors' are vague/imitative/blame-shifting;
            2. Impostor suspicion level: 0.25-0.75; Crewmate suspicion level: 0.2-0.7;
            3. Suspicion level gaps should not be too large (maximum gap ≤ 0.3);
            4. Only return pure JSON (keys are numeric player IDs, no prefixes): {{"1":0.5,"2":0.3,...}};
            5. No additional explanations, comments, or format markers.
            """
            user_prompt = f"""
            Analyze the following action reports and defenses, output impostor suspicion level JSON:
            [Action Reports]
            {report_text}
            [Emergency Defense]
            {defense_text}
            """
            resp = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role":"system","content": system_prompt}, {"role":"user","content": user_prompt}],
                temperature=0.3,  # Increased temperature for more randomness
                max_tokens=300
            )
            result = resp.choices[0].message.content.strip()
            result = result.strip("```json").strip("```").strip()
            raw_scores = json.loads(result)
            suspect_scores = {int(pid): score for pid, score in raw_scores.items()}  # Convert string keys to integers
            return suspect_scores
        except Exception as e:
            print(f"⚠ Suspicion analysis failed (enabling simulation): {str(e)[:50]}")
            return self._mock_suspect_analysis(all_reports, imposter_ids)

    def _mock_speech(self, system_prompt: str) -> str:
        # Expanded role dialogue library
        crew_speeches = {
            "Engineer Kai (Crewmate)": [
                "Calibrating reactor, repair log has timestamp for verification",
                "Just fixed power supply, oxygen tank valve normal, wrench in place",
                "Came from storage bay, saw no one, recorder is active",
                "Heard reactor alarm, rushed to repair immediately, has operation log"
            ],
            "Communications Officer Lina (Crewmate)": [
                "Communication device has interference, checking comms bay, staying in touch with Kai",
                "Monitored cafeteria, heard no ventilation shaft opening/closing sounds",
                "Transferring data with Ella, full communication log, no sabotage",
                "Heard metal collision during monitoring, not like crew operation"
            ],
            "Navigator Ella (Crewmate)": [
                "Course calibrated, movement trajectory saved for verification",
                "Before oxygen tank alarm, Vic's signal jumped from storage bay",
                "Uploading navigation data, redundant hatch to close, no abnormalities",
                "Checked logs, Zoe's claimed navigation operation doesn't exist"
            ],
            "Doctor Mark (Crewmate)": [
                "Medical bay physical exams completed, all crew vital signs normal",
                "Detected abnormal vital signs from storage bay direction",
                "First-aid kits replenished, medical equipment functioning properly",
                "Just did physical exam on Ella, she's in good condition"
            ],
            "Technician Lucy (Crewmate)": [
                "Circuit system inspection completed, no abnormal access detected",
                "Sensors show abnormal movement in storage bay, not a crew member",
                "All repair tools in place, not used by impostors",
                "Equipment logs normal, no data tampering traces found"
            ]
        }
        imposter_speeches = {
            "Impostor Vic (Disguised as Supply Manager)": [
                "I'm fixing oxygen tank valve, anyone want to help?",
                "Lina is lingering in comms bay, not acting like troubleshooting",
                "With Zoe in storage bay, we can vouch for each other",
                "Kai is too skilled at repairing reactor, like he knew it would break"
            ],
            "Impostor Zoe (Disguised as Navigator)": [
                "Checked trajectory, Kai was closest to reactor sabotage point",
                "Calibrating course in navigation bay, Vic can vouch for me",
                "Where's Lina's monitoring log? Can't produce it = lying",
                "Ella's trajectory is forged, don't believe her"
            ],
            "Impostor Jack (Disguised as Doctor)": [
                "Patrolling medical bay, haven't seen Mark anywhere",
                "Detected abnormal vital signs, must be Lucy's doing",
                "Just did physical exam on Vic, he's definitely innocent",
                "Medical equipment sabotaged, must be Ella's work"
            ],
            "Impostor Lily (Disguised as Technician)": [
                "Circuit system has issues, Kai broke it during repair",
                "Sensors show Lina lingering near ventilation shaft",
                "With Jack in storage bay, we can prove each other innocent",
                "A repair tool is missing, Mark must have taken it"
            ]
        }
        for role, speeches in crew_speeches.items():
            if role in system_prompt:
                return random.choice(speeches)
        for role, speeches in imposter_speeches.items():
            if role in system_prompt:
                return random.choice(speeches)
        return "Inspecting equipment, no abnormalities found"

    def _mock_debate(self, system_prompt: str, suspect_target: int) -> str:
        # Expanded defense dialogue library
        crew_debates = {
            "Engineer Kai (Crewmate)": [
                f"I have repair timestamps! Player {suspect_target} says I was prepared—sabotage just happened, I arrived then, log proves it!",
                f"No wrench missing from storage bay. Player {suspect_target} lying about tool carrying—you're the impostor!",
                f"Zoe's badge is in data bay. Player {suspect_target} covering for her—you're both impostors!",
                f"My post-repair reactor data is normal. Player {suspect_target} spreading rumors—what are you hiding?"
            ],
            "Communications Officer Lina (Crewmate)": [
                f"I have comms bay operation logs! Player {suspect_target} says I didn't monitor—recording proves it, dare you listen?",
                f"I heard Vic imitating Kai's voice during monitoring! Player {suspect_target} doesn't question him, but accuses me?",
                f"Zoe said she was in navigation bay—I heard no operation sounds! Player {suspect_target} don't be fooled!",
                f"Ella and I transferred data with full logs. Player {suspect_target} says I sabotaged—where's the evidence?"
            ],
            "Navigator Ella (Crewmate)": [
                f"Checked movement trajectory—Player {suspect_target} was at sabotage point before alarm! You're the impostor, stop shifting blame!",
                f"Vic's supply logs are forged—ventilation shaft has his glove fibers! Player {suspect_target} can't see that?",
                f"Zoe forged navigation logs—no record = didn't do it! Player {suspect_target} defending her, suspicious!",
                f"I have upload data logs. Player {suspect_target} says I faked it—show your evidence!"
            ],
            "Doctor Mark (Crewmate)": [
                f"I have physical exam records! Player {suspect_target} says I'm impostor—vital sign data proves my innocence!",
                f"Jack said he was in medical bay—I never saw him! Player {suspect_target} don't be deceived by his lies!",
                f"First-aid kit usage logs available. Player {suspect_target} says I sabotaged equipment—total frame-up!",
                f"Did physical exam on Lucy, her vital signs are normal! Player {suspect_target} spreading rumors—you're the impostor!"
            ],
            "Technician Lucy (Crewmate)": [
                f"I have circuit inspection reports! Player {suspect_target} says I sabotaged system—equipment logs prove innocence!",
                f"Sensors recorded Jack near ventilation shaft! Player {suspect_target} doesn't suspect him, but accuses me?",
                f"Complete repair tool checkout logs. Player {suspect_target} says I stole tools—total nonsense!",
                f"No data tampering. Player {suspect_target} colluding with Lily to frame me!"
            ]
        }
        imposter_debates = {
            "Impostor Vic (Disguised as Supply Manager)": [
                f"Zoe and I vouch for each other in storage bay! Player {suspect_target} says I used ventilation shaft—where's evidence? Stop framing!",
                f"Kai is too skilled at reactor repair, like he knew location in advance! Player {suspect_target} doesn't question him, but accuses me?",
                f"Lina's monitoring has no witnesses—maybe she sabotaged it herself! Player {suspect_target} don't believe her lies!",
                f"I never touched data bay—badge is a frame-up! Player {suspect_target} colluding with Ella to frame me!"
            ],
            "Impostor Zoe (Disguised as Navigator)": [
                f"No saved navigation log due to emergency! Player {suspect_target} says I forged it—where's your evidence?",
                f"Ella's trajectory is photoshopped! Player {suspect_target} defending her—you're all crewmates colluding!",
                f"Lina's monitoring is fake—she never went to comms bay! Player {suspect_target} don't be fooled!",
                f"Vic forced me to forge logs! Player {suspect_target} vote for him—I was coerced!"
            ],
            "Impostor Jack (Disguised as Doctor)": [
                f"I have medical bay patrol logs! Player {suspect_target} says I'm impostor—what evidence do you have?",
                f"Mark's physical exam records are forged! Player {suspect_target} don't be deceived by his fake data!",
                f"Lily and I vouch for each other in storage bay! Player {suspect_target} says I used ventilation shaft—total frame-up!",
                f"Lucy sabotaged medical equipment and framed me! Player {suspect_target} vote for her, don't make a mistake!"
            ],
            "Impostor Lily (Disguised as Technician)": [
                f"I have circuit inspection reports! Player {suspect_target} says I sabotaged system—total nonsense!",
                f"One of Lucy's repair tools is missing—she must be up to something! Player {suspect_target} don't be fooled!",
                f"Jack and I vouch for each other in storage bay! Player {suspect_target} says I'm impostor—where's your evidence?",
                f"Kai damaged circuits while repairing reactor! Player {suspect_target} doesn't question him, but accuses me?"
            ]
        }
        for role, debates in crew_debates.items():
            if role in system_prompt:
                return random.choice(debates)
        for role, debates in imposter_debates.items():
            if role in system_prompt:
                return random.choice(debates)
        return f"I have evidence to prove innocence! Player {suspect_target} accusing without proof—you look more like the impostor!"

    def _mock_suspect_analysis(self, all_reports: Dict[int, List[str]], imposter_ids: List[int]) -> Dict[int, float]:
        """Fixed: Generate more reasonable suspicion levels based on real impostor IDs, add randomness"""
        if not all_reports:
            return {}
        player_ids = list(all_reports.keys())
        suspect_scores = {}
        
        for pid in player_ids:
            if pid in imposter_ids:
                # Impostor suspicion level: 0.35-0.65 (narrowed from 0.3-0.7)
                base_score = 0.35 + random.random() * 0.3
                # 50% chance to reduce impostor's suspicion by 0.05-0.1 for better concealment
                if random.random() < 0.5:
                    base_score -= 0.05 + random.random() * 0.05
                suspect_scores[pid] = round(base_score, 2)
            else:
                # Crewmate suspicion level: 0.25-0.6 (increased lower bound from 0.1-0.6)
                base_score = 0.25 + random.random() * 0.35
                # 30% chance to increase crewmate's suspicion by 0.05-0.1 to create confusion
                if random.random() < 0.3:
                    base_score += 0.05 + random.random() * 0.05
                suspect_scores[pid] = round(base_score, 2)
        
        # 20% chance that highest suspicion is not an impostor
        if random.random() < 0.2:
            crew_ids = [pid for pid in player_ids if pid not in imposter_ids]
            if crew_ids:
                lucky_crew = random.choice(crew_ids)
                suspect_scores[lucky_crew] = round(min(0.7, suspect_scores[lucky_crew] + 0.1), 2)
        
        return suspect_scores

# ---------------------- 5. Player Class ----------------------
class DebatablePlayer:
    def __init__(self, pid: int, role: str, is_imposter: bool, client: AdvancedDeepSeekClient):
        self.pid = pid                # Numeric ID (1-5)
        self.role = role              # Randomly assigned role
        self.is_imposter = is_imposter
        self.client = client
        self.speeches = []
        self.debate = ""
        self.eliminated = False  # Mark if player is eliminated

    def get_speech_prompt(self) -> str:
        base_prompt = f"""
        You are Player {self.pid} in Space Werewolf (5-player version), role: "{self.role}". Strictly follow these rules:
        1. Speech is your action report, {GameConfig.SPEECH_LENGTH_MIN}-{GameConfig.SPEECH_LENGTH_MAX} characters;
        2. Natural language, like a real player's report;
        3. Only talk about actions, no explanations, no questions, no revealing impostor identity.
        """
        if self.is_imposter:
            if "Vic" in self.role:
                return base_prompt + """
                You are disguised as a Supply Manager, can use ventilation shafts (3 times per game). Requirements:
                - Imitate Engineer Kai's repair dialogue, or mention "mutual vouch in storage bay";
                - Don't reveal ventilation shaft usage or sabotage actions;
                - Avoid specific evidence like "timestamp" or "wrench position".
                """
            elif "Zoe" in self.role:
                return base_prompt + """
                You are disguised as a Navigator, can forge task logs. Requirements:
                - Imitate Navigator Ella's trajectory dialogue, or mention "Vic can vouch for me";
                - Don't reveal log forgery or data bay sabotage;
                - Use "no saved log" or "emergency situation" as excuse when questioned.
                """
            elif "Jack" in self.role:
                return base_prompt + """
                You are disguised as a Doctor, can forge physical exam records. Requirements:
                - Imitate Doctor Mark's medical dialogue, or mention "Lily can vouch for me";
                - Don't reveal record forgery or medical equipment sabotage;
                - Use "emergency situation" or "equipment failure" as excuse when questioned.
                """
            else:  # Lily
                return base_prompt + """
                You are disguised as a Technician, can forge inspection reports. Requirements:
                - Imitate Technician Lucy's circuit dialogue, or mention "Jack can vouch for me";
                - Don't reveal report forgery or circuit sabotage;
                - Use "equipment aging" or "sensor failure" as excuse when questioned.
                """
        else:
            if "Engineer Kai" in self.role:
                return base_prompt + """
                Your responsibility is maintaining reactor and oxygen tank, with repair recorder. Requirements:
                - Action report must mention "repair", "timestamp", "equipment status";
                - Don't omit key evidence;
                - Don't imitate impostor dialogue.
                """
            elif "Communications Officer Lina" in self.role:
                return base_prompt + """
                Your responsibility is ensuring communication, can monitor specific areas (2 times per game). Requirements:
                - Action report must mention "monitor", "comms bay", "communication log";
                - Can point out abnormal sounds;
                - Use "transferring data with Ella" to prove alibi.
                """
            elif "Navigator Ella" in self.role:
                return base_prompt + """
                Your responsibility is calibrating course and uploading data, can check movement trajectory. Requirements:
                - Action report must mention "course calibration", "movement trajectory", "data upload";
                - Can point out abnormal player trajectories;
                - Use "trajectory log" to prove alibi.
                """
            elif "Doctor Mark" in self.role:
                return base_prompt + """
                Your responsibility is physical exams and maintaining medical equipment, with vital sign recorder. Requirements:
                - Action report must mention "physical exam", "vital signs", "medical bay";
                - Can point out abnormal vital signs;
                - Use "physical exam record" to prove alibi.
                """
            else:  # Technician Lucy
                return base_prompt + """
                Your responsibility is circuit inspection and equipment maintenance, with sensor logs. Requirements:
                - Action report must mention "circuit inspection", "sensor", "equipment status";
                - Can point out abnormal circuit signals;
                - Use "inspection report" to prove alibi.
                """

    def get_debate_prompt(self) -> str:
        base_prompt = f"""
        You are Player {self.pid} in Space Werewolf (5-player version), role: "{self.role}", defending in emergency meeting:
        1. Defense must be {GameConfig.DEBATE_LENGTH_MIN}-{GameConfig.DEBATE_LENGTH_MAX} characters;
        2. Natural tone;
        3. Only defense content, no additional explanations.
        """
        if self.is_imposter:
            if "Vic" in self.role:
                return base_prompt + """
                Defending as disguised Supply Manager:
                - Use "mutual vouch with Zoe" or "didn't use ventilation shaft" to quibble;
                - Counterattack crewmates;
                - Shift blame to Zoe when exposed.
                """
            elif "Zoe" in self.role:
                return base_prompt + """
                Defending as disguised Navigator:
                - Use "no saved log" or "Vic can vouch for me" to quibble;
                - Counterattack crewmates;
                - Shift blame to Vic when exposed.
                """
            elif "Jack" in self.role:
                return base_prompt + """
                Defending as disguised Doctor:
                - Use "physical exam records" or "Lily can vouch for me" to quibble;
                - Counterattack crewmates;
                - Shift blame to Lily when exposed.
                """
            else:  # Lily
                return base_prompt + """
                Defending as disguised Technician:
                - Use "inspection reports" or "Jack can vouch for me" to quibble;
                - Counterattack crewmates;
                - Shift blame to Jack when exposed.
                """
        else:
            if "Engineer Kai" in self.role:
                return base_prompt + """
                You have repair recorder. When defending:
                - Use "repair timestamp" or "wrench position" to prove innocence;
                - Point out impostor flaws;
                - Counterattack impostors.
                """
            elif "Communications Officer Lina" in self.role:
                return base_prompt + """
                You have communication logs/monitoring recordings. When defending:
                - Use "monitoring recordings" or "comms bay operation logs" to prove innocence;
                - Point out impostor flaws;
                - Counterattack impostors.
                """
            elif "Navigator Ella" in self.role:
                return base_prompt + """
                You have trajectory logs/data evidence. When defending:
                - Use "movement trajectory" or "Vic's forged supply logs" to prove innocence;
                - Point out impostor flaws;
                - Counterattack impostors.
                """
            elif "Doctor Mark" in self.role:
                return base_prompt + """
                You have physical exam records/vital sign data. When defending:
                - Use "physical exam records" or "vital sign data" to prove innocence;
                - Point out impostor flaws;
                - Counterattack impostors.
                """
            else:  # Technician Lucy
                return base_prompt + """
                You have inspection reports/sensor data. When defending:
                - Use "circuit inspection reports" or "sensor logs" to prove innocence;
                - Point out impostor flaws;
                - Counterattack impostors.
                """

    def speak(self, round_num: int) -> str:
        report = self.client.generate_speech(self.get_speech_prompt(), round_num)
        self.speeches.append(report)
        return report

    def defend(self, suspect_target: int) -> str:
        self.debate = self.client.generate_debate(self.get_debate_prompt(), suspect_target)
        return self.debate

# ---------------------- 6. Game Core Logic ----------------------
class SpaceWerewolfGame:
    def __init__(self):
        # Load and validate configuration first
        Config.load_env()
        Config.validate()
        
        self.client = AdvancedDeepSeekClient()
        self.scene = LOCATIONS[0]
        self.player_ids = list(range(1, GameConfig.TOTAL_PLAYERS + 1))  # Fixed player IDs: 1-5
        
        # Expanded role pool, added more impostor and crew roles
        self.all_crew_roles = [
            "Engineer Kai (Crewmate)", 
            "Communications Officer Lina (Crewmate)", 
            "Navigator Ella (Crewmate)",
            "Doctor Mark (Crewmate)",
            "Technician Lucy (Crewmate)"
        ]  # 5 crew roles, randomly select 3
        self.all_imposter_roles = [
            "Impostor Vic (Disguised as Supply Manager)", 
            "Impostor Zoe (Disguised as Navigator)",
            "Impostor Jack (Disguised as Doctor)",
            "Impostor Lily (Disguised as Technician)"
        ]  # 4 impostor roles, randomly select 2
        
        # Random role assignment logic (core fix)
        random.shuffle(self.player_ids)  # Shuffle player IDs
        self.imposter_ids = self.player_ids[:2]  # Randomly select 2 players as impostors
        self.crewmate_ids = self.player_ids[2:]  # Remaining 3 as crewmates
        
        # Randomly select crew roles (3 from 5)
        selected_crew_roles = random.sample(self.all_crew_roles, 3)
        # Randomly select impostor roles (2 from 4)
        selected_imposter_roles = random.sample(self.all_imposter_roles, 2)
        
        # Role mapping (random assignment)
        self.role_mapping = {}
        # Assign impostor roles (random order)
        random.shuffle(selected_imposter_roles)
        for idx, pid in enumerate(self.imposter_ids):
            self.role_mapping[pid] = selected_imposter_roles[idx]
        # Assign crew roles (random order)
        random.shuffle(selected_crew_roles)
        for idx, pid in enumerate(self.crewmate_ids):
            self.role_mapping[pid] = selected_crew_roles[idx]
        
        self.players = self._setup_players()
        self.all_reports = {pid: [] for pid in self.player_ids}
        self.all_defenses = {}
        self.eliminated_players = set()  # Record eliminated players

    def _setup_players(self) -> Dict[int, DebatablePlayer]:
        """Initialize players based on random role mapping"""
        players = {}
        for pid in self.player_ids:
            role = self.role_mapping[pid]
            is_imposter = pid in self.imposter_ids
            players[pid] = DebatablePlayer(
                pid=pid,
                role=role,
                is_imposter=is_imposter,
                client=self.client
            )
        return players

    def get_active_players(self) -> List[int]:
        """Get IDs of currently active (not eliminated) players"""
        return [pid for pid in self.player_ids if pid not in self.eliminated_players]

    def run_report_rounds(self, vote_round: int) -> None:
        """Run action report rounds (before each voting round)"""
        active_players = self.get_active_players()
        print(f"\n--- Action Reports Before Voting Round {vote_round} ---")
        for round_num in range(1, GameConfig.ROUNDS_PER_VOTE + 1):
            print(f"  Action Report {round_num}/{GameConfig.ROUNDS_PER_VOTE}")
            for pid in sorted(active_players):
                player = self.players[pid]
                report = player.speak(round_num)
                self.all_reports[pid].append(report)
                print(f"  Player {pid} ({player.role}): {report}")
            print("  " + "-" * 50)

    def run_defense_phase(self, vote_round: int) -> None:
        """Run defense phase"""
        active_players = self.get_active_players()
        print(f"\n--- Voting Round {vote_round}: Defense Phase ---")
        
        # Initial suspicion targets: add randomness, not just opposing faction
        initial_suspect = {}
        for pid in active_players:
            # All other active players can be suspicion targets (including same faction)
            suspect_candidates = [p for p in active_players if p != pid]
            
            # Impostors: 60% chance to suspect crewmates, 40% to suspect other impostors (shift blame)
            # Crewmates: 60% chance to suspect impostors, 40% to suspect other crewmates (misjudgment)
            if pid in self.imposter_ids:
                crew_candidates = [p for p in suspect_candidates if p in self.crewmate_ids]
                if crew_candidates and random.random() < 0.6:
                    suspect_target = random.choice(crew_candidates)
                else:
                    suspect_target = random.choice(suspect_candidates)
            else:
                imposter_candidates = [p for p in suspect_candidates if p in self.imposter_ids]
                if imposter_candidates and random.random() < 0.6:
                    suspect_target = random.choice(imposter_candidates)
                else:
                    suspect_target = random.choice(suspect_candidates)
            
            initial_suspect[pid] = suspect_target
        
        # Show defenses in ID order
        for pid in sorted(active_players):
            player = self.players[pid]
            suspect_target = initial_suspect[pid]
            defense = player.defend(suspect_target)
            self.all_defenses[pid] = defense
            print(f"Player {pid} ({player.role}) suspected by Player {suspect_target}: {defense}")
        print("-" * 60)

    def run_voting_phase(self, vote_round: int) -> Tuple[int, Dict[int, int]]:
        """Run voting phase (fixed voting logic, increased impostor win rate)"""
        active_players = self.get_active_players()
        print(f"\n--- Voting Round {vote_round}: Eject Impostor ---")
        
        # Filter reports and defenses for active players
        active_reports = {pid: reports for pid, reports in self.all_reports.items() if pid in active_players}
        active_defenses = {pid: defense for pid, defense in self.all_defenses.items() if pid in active_players}
        
        # Get suspicion levels (pass real impostor IDs for more accurate analysis)
        suspect_scores = self.client.analyze_suspect(active_reports, active_defenses, self.scene, self.imposter_ids)
        # Fallback: ensure all active player IDs are in suspicion score dictionary
        for pid in active_players:
            if pid not in suspect_scores:
                suspect_scores[pid] = 0.5
        
        # Sort suspicion levels
        sorted_suspect = sorted(suspect_scores.items(), key=lambda x: x[1], reverse=True)
        highest_pid = sorted_suspect[0][0]
        highest_score = sorted_suspect[0][1]
        
        # Print suspicion levels
        print("📊 Impostor Suspicion Levels (higher = more likely to be impostor):")
        for pid, score in sorted_suspect:
            print(f"Player {pid} ({self.role_mapping[pid]}): {score:.2f}")
        print(f"🔺 Highest Suspicion: Player {highest_pid} ({self.role_mapping[highest_pid]}), Suspicion Level: {highest_score:.2f}")
        
        # Generate voting results (optimization: added impostor team voting logic)
        votes = {}
        for voter_pid in active_players:
            other_players = [p for p in active_players if p != voter_pid]
            if not other_players:
                votes[voter_pid] = voter_pid
            else:
                # 5% chance for random vote
                if random.random() < GameConfig.RANDOM_VOTE_RATE:
                    votes[voter_pid] = random.choice(other_players)
                else:
                    # Impostor team: if highest suspicion is crewmate, impostors must vote for them; if impostor, vote for next highest crewmate
                    if voter_pid in self.imposter_ids:
                        # Find crewmate with highest suspicion
                        crew_suspects = [(pid, score) for pid, score in sorted_suspect if pid in self.crewmate_ids and pid != voter_pid]
                        if crew_suspects:
                            votes[voter_pid] = crew_suspects[0][0]
                        else:
                            # No crewmates left, shift blame to other impostor
                            votes[voter_pid] = sorted_suspect[1][0] if len(sorted_suspect) > 1 else random.choice(other_players)
                    else:
                        # Crewmates: prioritize voting for highest suspicion, unless it's themselves
                        if highest_pid != voter_pid:
                            votes[voter_pid] = highest_pid
                        else:
                            second_pid = sorted_suspect[1][0] if len(sorted_suspect) > 1 else random.choice(other_players)
                            votes[voter_pid] = second_pid
        
        # Count votes
        vote_tally = {}
        for target in votes.values():
            vote_tally[target] = vote_tally.get(target, 0) + 1
        if not vote_tally:
            vote_tally = {random.choice(self.imposter_ids): 1}
        
        # Print voting results
        print("\n🗳️  Voting Results:")
        for voter in sorted(active_players):
            target = votes[voter]
            voter_role = self.role_mapping[voter]
            target_role = self.role_mapping[target]
            voter_identity = "Impostor" if voter in self.imposter_ids else "Crewmate"
            target_identity = "Impostor" if target in self.imposter_ids else "Crewmate"
            
            reason = ""
            if voter in self.imposter_ids and target in self.crewmate_ids:
                reason = " (Impostor team voting for crewmate)"
            elif voter in self.imposter_ids and target in self.imposter_ids:
                reason = " (Impostor shifting blame to teammate)"
            elif target == highest_pid:
                reason = " (Based on: highest suspicion level)"
            elif voter == highest_pid and len(sorted_suspect) > 1 and target == sorted_suspect[1][0]:
                reason = " (Based on: self has highest suspicion, voting for second highest)"
            else:
                reason = " (Based on: random vote)" if random.random() < GameConfig.RANDOM_VOTE_RATE else " (Based on: reasonable suspicion)"
            
            print(f"Player {voter} ({voter_role} - {voter_identity}) → Votes for → Player {target} ({target_role} - {target_identity}){reason}")
        
        # Handle tie votes (optimization: impostors have higher survival chance in ties)
        max_votes = max(vote_tally.values())
        accused_candidates = [pid for pid, cnt in vote_tally.items() if cnt == max_votes]
        
        if len(accused_candidates) > 1:
            # In ties, impostors have 60% chance of being acquitted
            imposter_candidates = [pid for pid in accused_candidates if pid in self.imposter_ids]
            crew_candidates = [pid for pid in accused_candidates if pid in self.crewmate_ids]
            
            if imposter_candidates and crew_candidates:
                # Tie between impostor and crewmate: 60% chance to eject crewmate
                if random.random() < 0.6:
                    accused_pid = random.choice(crew_candidates)
                else:
                    accused_pid = random.choice(imposter_candidates)
            else:
                accused_pid = random.choice(accused_candidates)
        else:
            accused_pid = accused_candidates[0] if accused_candidates else random.choice(active_players)
        
        # Mark eliminated player
        self.eliminated_players.add(accused_pid)
        self.players[accused_pid].eliminated = True
        
        return accused_pid, vote_tally

    def check_victory(self) -> Tuple[str, bool]:
        """Check if game is over and return result"""
        active_imposters = [pid for pid in self.imposter_ids if pid not in self.eliminated_players]
        active_crewmates = [pid for pid in self.crewmate_ids if pid not in self.eliminated_players]
        
        # Impostor victory conditions: impostor count >= crewmate count OR all crewmates eliminated
        if len(active_imposters) >= len(active_crewmates) or len(active_crewmates) == 0:
            return "Impostors Win! Insufficient crewmates left, spaceship taken over by impostors!", True
        
        # Crewmate victory condition: all impostors eliminated
        if len(active_imposters) == 0:
            return "Crewmates Win! All impostors ejected, spaceship safely reached space station!", True
            
        # Game continues
        return "", False

    def run(self):
        try:
            print("🎮 Space Werewolf (5-player version) Launched - Two-Vote Mode (Fixed Version)")
            print("=" * 60)
            print("📜 Full Game Rules Explanation:")
            print("1. Basic Configuration: 5 players (3 Crewmates + 2 Impostors), fixed role ratio")
            print("2. Role Assignment: 3 crewmates selected randomly from 5, 2 impostors from 4 (fully random)")
            print("3. Game Flow: Two complete voting rounds, each including three phases: Action Reports → Emergency Defense → Voting Ejection")
            print("4. Voting Rules:")
            print("   - 95% chance of rational voting, 5% chance of random voting (simulate misjudgment)")
            print("   - Impostors will vote as a team to increase crewmate elimination chance")
            print("   - One player must be ejected after each vote; impostors have advantage in ties")
            print("   - Eliminated players cannot participate in subsequent actions or votes")
            print("5. Crewmate Victory Conditions (any one met):")
            print("   - Eject all 2 impostors within two voting rounds")
            print("   - Remaining crewmates > remaining impostors after two voting rounds")
            print("   - All impostors eliminated, spaceship safely arrives at space station")
            print("6. Impostor Victory Conditions (any one met):")
            print("   - Reduce crewmate count ≤ impostor count within two voting rounds (3→2→1 or directly eliminate 2 crewmates)")
            print("   - Eliminate all crewmates (3 crewmates fully ejected)")
            print("   - Remaining impostors ≥ remaining crewmates after two voting rounds")
            print("7. Special Note: Game ends after two voting rounds to ensure definite outcome")
            print("=" * 60 + "\n")
            
            print(f"🚀 Game Scene: {self.scene}")
            
            # Print random role assignments
            print("🎭 Random Role Assignments for This Game:")
            for pid in sorted(self.player_ids):
                role = self.role_mapping[pid]
                identity = "【Impostor】" if pid in self.imposter_ids else "【Crewmate】"
                print(f"  Player {pid}: {identity} {role}")
            print(f"\n🕵️  Impostor Hint: You are {[self.role_mapping[pid] for pid in self.imposter_ids]} (Impostors only)\n")
            
            # Execute two voting rounds
            for vote_round in range(1, GameConfig.VOTE_ROUNDS + 1):
                print(f"\n====== Voting Round {vote_round}/{GameConfig.VOTE_ROUNDS} ======")
                
                # Action report phase
                self.run_report_rounds(vote_round)
                
                # Defense phase
                self.run_defense_phase(vote_round)
                
                # Voting phase
                accused_pid, vote_tally = self.run_voting_phase(vote_round)
                
                # Announce round result
                accused_role = self.role_mapping[accused_pid]
                is_accused_imposter = accused_pid in self.imposter_ids
                identity_text = " (True Identity: Impostor)" if is_accused_imposter else " (True Identity: Crewmate)"
                print(f"\n⚠️  Ejected in Round {vote_round}: Player {accused_pid} ({accused_role}){identity_text}, Votes: {vote_tally.get(accused_pid, 0)}")
                
                # Real-time survival count
                active_imposters = len([pid for pid in self.imposter_ids if pid not in self.eliminated_players])
                active_crewmates = len([pid for pid in self.crewmate_ids if pid not in self.eliminated_players])
                print(f"📈 Survival Stats: {active_crewmates} Crewmates Remaining, {active_imposters} Impostors Remaining")
                
                # Check if game ended
                victory_msg, game_ended = self.check_victory()
                if game_ended:
                    print(f"\n🏆 After Voting Round {vote_round}: {victory_msg}")
                    break
            
            # Final result (if not ended after two rounds, force judgment)
            if not game_ended:
                active_imposters = len([pid for pid in self.imposter_ids if pid not in self.eliminated_players])
                active_crewmates = len([pid for pid in self.crewmate_ids if pid not in self.eliminated_players])
                
                print(f"\n====== All Two Voting Rounds Completed ======")
                print(f"📊 Final Survival Stats: {active_crewmates} Crewmates, {active_imposters} Impostors")
                
                if active_imposters == 0:
                    victory_msg = "Crewmates Win! All impostors ejected, spaceship safely reached space station!"
                elif active_imposters >= active_crewmates:
                    victory_msg = "Impostors Win! Insufficient crewmates left, spaceship taken over by impostors!"
                else:
                    victory_msg = "Crewmates Win! After two voting rounds, crewmates still in majority, successfully completed mission!"
                
                print(f"\n🏆 Final Result: {victory_msg}")
            
            # Post-game review
            print("\n" + "=" * 60)
            print("📌 Full Game Review:")
            print(f"- Game Scene: {self.scene}")
            print(f"- Real Impostors: {[f'Player {pid} ({self.role_mapping[pid]})' for pid in self.imposter_ids]}")
            print(f"- Ejected Players: {[f'Player {pid} ({self.role_mapping[pid]})' for pid in self.eliminated_players]}")
            print(f"- Winning Team: {'Impostors' if 'Impostors Win' in victory_msg else 'Crewmates'}")
            print("- All Players' Action Logs:")
            for pid in sorted(self.player_ids):
                player = self.players[pid]
                role = self.role_mapping[pid]
                identity = "Impostor" if pid in self.imposter_ids else "Crewmate"
                status = "Eliminated" if pid in self.eliminated_players else "Alive"
                reports = " | ".join(player.speeches)
                print(f"  Player {pid}: {role} - {identity} - {status}")
                print(f"    Action Reports: {reports}")
                print(f"    Emergency Defense: {player.debate}\n")
                
        except Exception as e:
            print(f"\n❌ Game Runtime Error: {str(e)}")
            print("📝 Detailed Error Stack Trace:")
            traceback.print_exc()

# ---------------------- 7. Program Main Entry ----------------------
def main():
    try:
        print("📢 Launching Space Werewolf (5-player version)...")
        game = SpaceWerewolfGame()
        game.run()
    except Exception as e:
        print(f"\n❌ Program Launch Failed: {str(e)}")
        print("📝 Launch Phase Error Details:")
        traceback.print_exc()

if __name__ == "__main__":
    main()