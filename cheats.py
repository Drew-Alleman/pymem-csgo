import requests
import win32api
import time
import pymem

VERSION = "1.0.1"

try:    
    hazedumper = requests.get("https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.json").json()
except (ValueError, requests.RequestException):
    exit("[-] Failed to fetch the latests offsets from hazedumper!")

try:
    csgo = pymem.Pymem("csgo.exe")
except pymem.exception.ProcessNotFound:
    exit("[-] Failed to start cheats CS:GO is not currently running")

module_base = pymem.process.module_from_name(csgo.process_handle, "client.dll").lpBaseOfDll

if not module_base:
    exit("[-] Failed to load module: 'client.dll'")

class CEntity:
    """ CSGO Entity class 
    Used to control and monitor player entites in CSGO
    """

    def __bool__(self) -> bool:
        """ Checks to see if the current entity is valid
        1. Checks to see if the current memory address is valid
        2. Checks to see if the current entity is alive
        3. Checks to see if the current entity is dormant
        :return: True if the entity is valid
        """
        return self.address > 0 and self.is_alive() and not self.is_dormant()

    def __init__(self, address) -> None:
        """ Defines a CSGO Player Entity
        :param address: Memory address of entity
        """
        self.address = address

    def get_health(self) -> int:
        """ Fetches the entitys current health
        :return: Entity's Health
        """
        return csgo.read_int(self.address + hazedumper["netvars"]["m_iHealth"])
    
    def is_alive(self) -> bool:
        """ Checks to see if the current entity is alive
        :return: True if the entity is alive
        """
        return self.get_health() > 0

    def is_dormant(self) -> bool:
        """ Checks to see if the player is AFK / Too far away
        :return: True if the current entity is dormant
        """
        return csgo.read_bool(self.address + hazedumper["signatures"]["m_bDormant"])
    
    def get_team_number(self) -> int:
        """ Gets the current entities team number
        :return int: Team number
        2 -> Terroist
        3 -> Counter-terrorist
        """
        return csgo.read_int(self.address + hazedumper["netvars"]["m_iTeamNum"])
    
    def spot(self) -> None:
        """ Used to set the entity as spotted on the radar
        """
        csgo.write_bool(self.address + hazedumper["netvars"]["m_bSpotted"], True)

    def is_defusing(self) -> bool:
        """ Checks to see if the current player is defusing
        :return: True if the player is defusing
        """
        return csgo.read_bool(self.address + hazedumper["netvars"]["m_bIsDefusing"])

    def glow(self, r: float, g:float, b: float, a:float = 1) -> None:
        """ Applies glow to an entity
        :param r: Red value
        :param g: Green value
        :param b: Blue value
        :param a: Alpha value
        """
        glow_manager = csgo.read_int(module_base + hazedumper["signatures"]["dwGlowObjectManager"])
        entity_glow = csgo.read_int(self.address + hazedumper["netvars"]["m_iGlowIndex"])
        entity = glow_manager + entity_glow * 0x38
        if entity +  0x8 < 0:
            return
        csgo.write_float(entity +  0x8, float(r))  # R
        csgo.write_float(entity + 0xC, float(g))   # G
        csgo.write_float(entity + 0x10, float(b))  # B
        csgo.write_float(entity + 0x14, float(a))  # Alpha
        csgo.write_int(entity + 0x28, 1)           # m_bRenderWhenOccluded
        csgo.write_int(entity + 0x29, 0)           # m_bRenderWhenUnoccluded

    def glow_by_health(self) -> None:
        """ Glows the entity depending on how much health they have 
        """
        entity_health = self.get_health()
        if entity_health < 30:
            self.glow(1, 0, 0) # Glow Red
        elif entity_health < 50:
            self.glow(1, 1, 0) # Glow yellow
        else:
            self.glow(0, 1, 0) # Glow green

class LocalPlayer(CEntity):
    """ Class used to monitor the localplayer
    """
    def update(self):
        """ updates the localplayers memory address
        """
        self.address = csgo.read_int(module_base + hazedumper["signatures"]["dwLocalPlayer"])

    def update_or_loop(self) -> None:
        """ Updates the localplayer address, if the update
        returns an invalid address the function will loop and sleep
        until a valid memory address if found
        """
        self.update()
        while self.address <= 0:
            self.update()
            time.sleep(1.5)

    def glow_ent(self, c_entity: CEntity) -> None:
        """ Glow the specifed entity to the localplayer
        :param c_entity: Entity to glow 
        """
        if c_entity.get_team_number() == self.get_team_number():
            c_entity.glow(0, 0, 1) # Glow blue
        elif c_entity.is_defusing():
            c_entity.glow(1, 0, 1) # Glow purple
        else:
            c_entity.glow_by_health()  # Glow depending on there health
    
def main() -> None:
    """ Starts the CSGO Cheats
    """
    localplayer = LocalPlayer(None)
    while True:
        if win32api.GetKeyState(117): # Kill switch (F6)
            break
        localplayer.update_or_loop() # blocks
        for i in range(1, 32):
            if not localplayer.is_alive():
                break
            entity_address = csgo.read_int(module_base + hazedumper["signatures"]["dwEntityList"] + i * 0x10)
            if entity_address <= 0: # If the entity is not a valid memory address
                continue
            c_entity = CEntity(entity_address)
            if not bool(c_entity):
                continue
            localplayer.glow_ent(c_entity)
            c_entity.spot()
        time.sleep(.05)

if __name__ == '__main__':
    print("[*] Started CSGO cheats")
    main()
