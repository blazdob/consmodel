from utils.st_types import StorageType
from scipy import optimize
import pandas as pd
import warnings

from base_model import BaseModel

class Battery(BaseModel):
	"""
	Class to represent a battery.
	
	Attributes
	----------
	id : int
		Unique identifier.
	name : str
		Name of the battery.
	st_type : str
		Storage type.
	max_charge_p_kw : float
		Maximum charging power in kW.
	max_discharge_p_kw : float
		Maximum discharging power in kW.
	max_e_kwh : float
		Maximum energy in kWh.
	soc : float
		State of charge.
	current_p_kw : float
		Current power in kW.
	remaining_e_kwh : float
		Current remaining energy in kWh.
	
	Methods
	-------
	charge(p_kw, dt)
		Charge the battery.
	discharge(p_kw, dt)
		Discharge the battery.
	"""
	
	def __init__(self,
				lat,
				lon,
				alt,
				id: int = 0,
				name: str = "BS_default",
				TZ: str = None,
				use_utc: bool = False,
				st_type: str = None,
				max_charge_p_kw: float = 1.,
				max_discharge_p_kw: float = 1.,
				max_e_kwh: float = 1.,
				soc: float = 1.,
				):
		super().__init__(id, lat, lon, alt, name, TZ, use_utc)
		if st_type is None:
			self._id = id
			self._name = name
			self._max_charge_p_kw = max_charge_p_kw
			self._max_discharge_p_kw = max_discharge_p_kw
			self._max_e_kwh = max_e_kwh
		else:
			storage_type = StorageType(st_type)
			self._id = id
			self._name = storage_type.name
			self._max_charge_p_kw = storage_type.max_charge_p_kw
			self._max_discharge_p_kw = storage_type.max_discharge_p_kw
			self._max_e_kwh = storage_type.max_e_kwh

		self._soc = soc
		self._current_p_kw = 0
		self._current_e_kwh = self.max_e_kwh * soc
	
	def __repr__(self):
		return f"BS model(id={self.id}, name={self.name})"
	
	def __str__(self):
		return f"BS model(id={self.id}, name={self.name})"
	
	#__________________________________________________________________________
	# Properties
	#__________________________________________________________________________
	
	@property
	def id(self):
		return self._id
	
	@property
	def name(self):
		return self._name
	
	@property
	def max_charge_p_kw(self):
		return self._max_charge_p_kw
	
	@property
	def max_discharge_p_kw(self):
		return self._max_discharge_p_kw
	
	@property
	def max_e_kwh(self):
		return self._max_e_kwh
	
	@property
	def soc(self):
		return self._soc

	@property
	def current_p_kw(self):
		return self._current_p_kw
	
	@property
	def current_e_kwh(self):
		return self._current_e_kwh

	#__________________________________________________________________________
	# Setters
	#__________________________________________________________________________
	
	@id.setter
	def id(self, id):
		self._id = id
	
	@name.setter
	def name(self, name):
		self._name = name
	
	@max_charge_p_kw.setter
	def max_charge_p_kw(self, max_charge_p_kw):
		if not isinstance(max_charge_p_kw, float):
			raise TypeError("Max_charge_p_kw has to be a float.")
		if max_charge_p_kw < 0:
			raise ValueError("Max_charge_p_kw has to be larger than 0.")
		self._max_charge_p_kw = max_charge_p_kw
	
	@max_discharge_p_kw.setter
	def max_discharge_p_kw(self, max_discharge_p_kw):
		# has to be larger than 0
		if not isinstance(max_discharge_p_kw, float):
			raise TypeError("Max_discharge_p_kw has to be a float.")
		if max_discharge_p_kw < 0:
			raise ValueError("Max_discharge_p_kw has to be larger than 0.")
		self._max_discharge_p_kw = max_discharge_p_kw
	
	@max_e_kwh.setter
	def max_e_kwh(self, max_e_kwh):
		if not isinstance(max_e_kwh, float):
			raise TypeError("Max_e_kwh has to be a float.")
		if max_e_kwh < 0:
			raise ValueError("Max_e_kwh has to be larger than 0.")
		self._max_e_kwh = max_e_kwh
	
	@soc.setter
	def soc(self, soc):
		if not isinstance(soc, float):
			raise TypeError("SOC has to be a float.")
		if soc < 0 or soc > 1:
			raise ValueError("SOC must be between 0 and 1.")
		self._soc = soc

	@current_p_kw.setter
	def current_p_kw(self, current_p_kw):
		if not isinstance(current_p_kw, float):
			raise TypeError("Current_p_kw has to be a float.")
		if current_p_kw < -self.max_discharge_p_kw or current_p_kw > self.max_charge_p_kw:
			raise ValueError(f"Current_p_kw must be between -{self.max_discharge_p_kw} and {self.max_charge_p_kw}.")
		self._current_p_kw = current_p_kw
	
	@current_e_kwh.setter
	def current_e_kwh(self, current_e_kwh):
		if not isinstance(current_e_kwh, float):
			raise TypeError("current_e_kwh has to be a float.")
		if current_e_kwh < 0 or current_e_kwh > self.max_e_kwh:
			raise ValueError(f"current_e_kwh must be between 0 and {self.max_e_kwh}.")
		self._current_e_kwh = current_e_kwh

	#__________________________________________________________________________
	# Methods
	#__________________________________________________________________________

	def __repr__(self):
		return f"Battery(id={self.id}, name={self.name}, max_charge_p_kw={self.max_charge_p_kw}, max_discharge_p_kw={self.max_discharge_p_kw}, max_e_kwh={self.max_e_kwh}, soc={self.soc}, current_p_kw={self.current_p_kw}, remaining_e_kwh={self.current_e_kwh})"

	def charge(self, p_kw: float, dt: float):
		"""
		Charge the battery.

		Parameters
		----------
		p_kw : float
			Power in kW.
		dt : float
			Time in hours.
		"""
		if self.current_e_kwh + (p_kw * dt) <= self.max_e_kwh:
			self.current_p_kw = p_kw
			self.current_e_kwh += p_kw * dt
		else:
			# give a warning that the battery can not be charged more
			self.current_p_kw = (self.max_e_kwh - self.current_e_kwh)/dt
			self.current_e_kwh = self.max_e_kwh
			# raise warning
			warnings.warn("Battery can not be charged for {} kW for {} hours as it has reached full capacity. \n The battery has been charged to full capacity".format(p_kw, dt))
		self.soc = self.current_e_kwh / self.max_e_kwh
	
	def discharge(self, p_kw: float, dt: float):
		"""
		Discharge the battery.

		Parameters
		----------
		p_kw : float
			Power in kW.
		dt : float
			Time in hours.
		"""
		if self.current_e_kwh - p_kw * dt >= 0:
			self.current_p_kw = p_kw
			self.current_e_kwh -= p_kw * dt
		else:
			# give a warning that the battery can not be discharged more
			self.current_p_kw = self.current_e_kwh / dt
			self.current_e_kwh = 0.
			# raise warning
			warnings.warn("Battery can not be discharged for {} kW for {} hours as it has reached empty capacity. \n The battery has been discharged to empty capacity".format(p_kw, dt))
		self.soc = self.current_e_kwh / self.max_e_kwh

	def model(self,
					control_type: str = "production_saving",
					p_kw: pd.DataFrame() = None,
				):
		"""
		Model the controller and run it.

		Parameters
		----------
		control_type : str
			control_type of simulation, where options are "production_saving" and "installed_power".
		p_kw : pd.DataFrame()
			Power in kW in 15 min intervals where the index is the timestamp.
			in a format:
			|      Timestamp      |     P      |
			|---------------------|------------|
			| 2020-01-01 00:00:00 |    0.0     |
			| 2020-01-01 00:15:00 |    0.0     |
			|         ...         |    ...     |
		"""
		if p_kw is None:
			raise ValueError("We need a timeseries data to simulate the battery.")
		lst = []
		self.results = p_kw
		self.results["battery_plus"] = 0.
		self.results["battery_minus"] = 0.

		if control_type == "production_saving": #ko je proizvodnja večja od porabe (imamo negativno moč) shranjujemo presežek v baterijo, ko je poraba večja baterijo praznimo.
			for key, df_tmp in self.results.iterrows():                
				if df_tmp.P > 0: # we have some consumption
					if self.current_e_kwh > 0: # if battery is not empty                        
						if self.current_e_kwh - 0.25*df_tmp.P > 0:                   
							self.discharge_amount = float(min(df_tmp.P, self.max_discharge_p_kw))
						else: # Battery does not have enought energy to discharge at full power for the next 15 min
							self.discharge_amount = float(min(self.max_discharge_p_kw, 4*self.current_e_kwh))
						self.discharge(self.discharge_amount, 0.25)
						self.results.loc[key, "battery_plus"] = self.discharge_amount
					else: 
						#we have an empty battery
						pass
				else: # we have some production
					if (self.current_e_kwh - 0.25*df_tmp.P) < self.max_e_kwh: # we can charge the battery at full capacity
						self.charge_amount = min(df_tmp.P*(-1), self.max_charge_p_kw)
					else:
						self.charge_amount = min(4*(self.max_e_kwh- self.current_e_kwh), self.max_charge_p_kw)
					self.charge(self.charge_amount, 0.25)
					self.results.loc[key, "battery_minus"] = -self.charge_amount
				lst.append(self.current_e_kwh) 
		elif control_type == "installed_power":
			p_limit = round(self.get_min_p_lim(), 1)
			self.curr_limit = p_limit
			self.hard_reset()
			for key, df_tmp in self.results.iterrows():
				if df_tmp.P > p_limit:
					if self.current_e_kwh > 0:
						#if battery is not empty
						self.discharge_amount = float(min(df_tmp.P - p_limit, self.max_discharge_p_kw))
						if self.current_e_kwh < self.discharge_amount*0.25:
							self.discharge_amount = self.current_e_kwh*4
						self.discharge(self.discharge_amount, 0.25) 
						self.results.loc[key, "battery_plus"] = self.discharge_amount
					else:
						#we have an empty battery
						pass
				else: # charging battery
					excess_power = p_limit - df_tmp.P
					if self.current_e_kwh < self._max_e_kwh:
						self.charge_amount = min(excess_power, self.max_charge_p_kw)
						if self.current_e_kwh + self.charge_amount*0.25 > self._max_e_kwh:
							self.charge_amount = (self.max_e_kwh - self.current_e_kwh)*4
						self.results.loc[key, "battery_minus"] = -self.charge_amount
						self.charge(self.charge_amount, 0.25)
					else:
						#we have a full battery
						pass
				lst.append(self.current_e_kwh)
		elif control_type == "5Tariff_manoeuvering": #hranilnik uporabljamo samo da prestavljamo energijo iz bolj obremenjenih blokov na manj obremenjene
			for key, df_tmp in self.results.iterrows():
				h = (key-pd.Timedelta(1, "min")).hour
				if h <= 5 or h >=22:
					n_hours = 8
					self.charge_amount = float(min(self._max_e_kwh/n_hours, (self._max_e_kwh-self.current_e_kwh)*4, self.max_charge_p_kw))
					self.discharge_amount = 0.
				elif h >= 7 and h <= 13:
					n_hours = 7
					self.discharge_amount = float(min(self._max_e_kwh/n_hours, (self.current_e_kwh)*4, self.max_discharge_p_kw))
					self.charge_amount = 0.
				elif h == 14 or h == 15:
					n_hours = 2
					self.charge_amount = float(min(self._max_e_kwh/n_hours, (self._max_e_kwh-self.current_e_kwh)*4, self.max_charge_p_kw))
					self.discharge_amount = 0.
				elif h >= 16 and h <= 19:
					n_hours = 4
					self.discharge_amount = float(min(self._max_e_kwh/n_hours, (self.current_e_kwh)*4, self.max_discharge_p_kw))
					self.charge_amount = 0.
				else:
					self.discharge_amount = 0.
					self.charge_amount = 0.
				self.charge(self.charge_amount, 0.25)
				self.discharge(self.discharge_amount, 0.25)
				lst.append(self.current_e_kwh)
				self.results.loc[key, "battery_plus"] = self.discharge_amount
				self.results.loc[key, "battery_minus"] = -self.charge_amount
	
		self.results["P_after"] = self.results.P - self.results.battery_plus - self.results.battery_minus
		self.results["var_bat"] = lst
		return self.results
	
	def simulate(self, control_type, p_kw):
		self.hard_reset()
		self.model(control_type=control_type, p_kw=p_kw)
		self.timeseries = self.results["P_after"]
		return self.timeseries

	def is_p_limit_posible(self, p_limit):
		for _, df_tmp in self.results.iterrows():
			if df_tmp.P > p_limit: # lower the peak
				if self.current_e_kwh >= 0: #if battery is not empty
					if df_tmp.P - p_limit > self.max_discharge_p_kw: 
						# not enough max output
						return -1
					needed_output = float(df_tmp.P - p_limit) # Lower te peak till p_limit
					if self.current_e_kwh < needed_output*0.25:
						# not enough energy
						return -1
					self.discharge_amount = needed_output
					self.discharge(self.discharge_amount, 0.25)
				else:
					#we have an empty battery
					return -1
			else:
				diff = p_limit - df_tmp.P # excess power to charge the battery
				self.charge_amount = float(min(diff, self.max_charge_p_kw))
				if self.current_e_kwh < self.max_e_kwh:
					if self.current_e_kwh + self.charge_amount*0.25 > self.max_e_kwh:
						self.charge_amount = float(self.max_e_kwh - self.current_e_kwh)*4
					self.charge(self.charge_amount, 0.25)
				else:
					pass
		return 1
	
	def get_min_p_lim(self):
		b = self.results.P.max()
		f = self.is_p_limit_posible
		root = optimize.bisect(f,b-self.max_discharge_p_kw-1,b, xtol=0.05)
		return root
	
	def soft_reset(self):
		"""
		Soft reset the battery.
		"""
		self.current_p_kw = 0.
		self.current_e_kwh = self.max_e_kwh * self.soc
	
	def hard_reset(self):
		"""
		Hard reset the battery.
		"""
		self.current_p_kw = 0.
		self.current_e_kwh = self.max_e_kwh
		self.soc = 1.

	def change_battery(self, max_e_kwh, max_charge_p_kw, max_discharge_p_kw=None):
		"""
		Change the battery size and params.

		Parameters
		----------
		max_e_kwh : float
			Maximum energy in kWh.
		max_p_kw : float
			Maximum power in kW.
		"""
		self.max_e_kwh = float(max_e_kwh)
		self.max_charge_p_kw = float(max_charge_p_kw)
		if max_discharge_p_kw is None:
			self.max_discharge_p_kw = float(max_charge_p_kw)
		else:
			self.max_discharge_p_kw = float(max_discharge_p_kw)
		self.hard_reset()
	
	def change_battery_by_type(self, st_type: str):
		"""
		Change the battery by type.

		Parameters
		----------
		st_type : str
			Storage type.
		"""
		storage_type = StorageType(st_type)
		self.max_e_kwh = storage_type.max_e_kwh
		self.max_charge_p_kw = storage_type.max_charge_p_kw
		self.max_discharge_p_kw = storage_type.max_discharge_p_kw
		self.name = storage_type.name
		self.hard_reset()

		
if __name__ == "__main__":
	test_data = pd.DataFrame({"P": [0.,-3.,-2.,8.,7.,6.,7.,8.,3.,5.,4.,-2.,0.,2.,0.,0.,0.]}, index=pd.date_range("2020-01-01 06:00:00", periods=17, freq="15min"))
	batt = Battery(lat=46.155768, lon=14.304951, alt=400, id=1, st_type="10kWh_5kW")
	timeseries = batt.simulate(control_type="installed_power",
					p_kw=test_data,
					)