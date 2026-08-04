import time
import requests
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.clock import Clock # <-- Importamos reloj para checar el estado en bucle
from plyer import gps

URL_SERVIDOR = "http://127.0.0.1:8000"

# --- PANTALLA 1: REGISTRO Y ESPERA DE APROBACIÓN ---
class PantallaRegistro(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.95, 0.95, 0.95, 1) 
        
        self.layout = BoxLayout(orientation='vertical', padding=25, spacing=10)
        
        # Escudo institucional
        self.escudo = Image(source='escudo.png', size_hint_y=None, height=120)
        self.layout.add_widget(self.escudo)
        
        self.layout.add_widget(Label(text="Registro Exclusivo: Establecimientos y Fraccionamientos", font_size=14, color=(0.3, 0.3, 0.3, 1)))
        
        # Campos de entrada
        self.negocio = TextInput(hint_text="Nombre del Establecimiento / Fraccionamiento", multiline=False, size_hint_y=None, height=45)
        self.encargado = TextInput(hint_text="Nombre completo del titular responsable", multiline=False, size_hint_y=None, height=45)
        
        self.layout.add_widget(Label(text="Validación de Mayoría de Edad (Obligatorio):", color=(0.8, 0, 0, 1), size_hint_y=None, height=25))
        self.curp = TextInput(hint_text="Folio de CURP", multiline=False, size_hint_y=None, height=45)
        
        self.btn_selfie = Button(text="📸 Tomar Selfie de Validación", background_color=(0.2, 0.5, 0.8, 1), size_hint_y=None, height=50)
        self.btn_selfie.bind(on_press=self.simular_captura)
        self.selfie_tomada = False 
        
        self.layout.add_widget(Label(text="Prueba de seguridad: ¿Cuánto es 5 + 4?", color=(0.3, 0.3, 0.3, 1), size_hint_y=None, height=25))
        self.antibot = TextInput(hint_text="Escriba el resultado con número", multiline=False, size_hint_y=None, height=45)
        
        self.mensaje_error = Label(text="", color=(1, 0, 0, 1), size_hint_y=None, height=25)
        
        self.btn_registrar = Button(text="Enviar Solicitud a Cabina", background_color=(0, 0.5, 0.2, 1), size_hint_y=None, height=55, bold=True)
        self.btn_registrar.bind(on_press=self.enviar_solicitud)
        
        self.layout.add_widget(self.negocio)
        self.layout.add_widget(self.encargado)
        self.layout.add_widget(self.curp)
        self.layout.add_widget(self.btn_selfie)
        self.layout.add_widget(self.antibot)
        self.layout.add_widget(self.mensaje_error)
        self.layout.add_widget(self.btn_registrar)
        
        self.add_widget(self.layout)

    def simular_captura(self, instance):
        self.btn_selfie.text = "✅ Selfie Capturada Correctamente"
        self.btn_selfie.background_color = (0, 0.6, 0.2, 1)
        self.selfie_tomada = True

    def enviar_solicitud(self, instance):
        self.mensaje_error.text = ""
        
        if not (self.negocio.text and self.encargado.text and self.curp.text):
            self.mensaje_error.text = "Error: Llene todos los campos de texto."
            return
            
        if not self.selfie_tomada:
            self.mensaje_error.text = "Error: La selfie de validación es obligatoria."
            return
            
        if self.antibot.text.strip() != "9":
            self.mensaje_error.text = "Error: Prueba de seguridad incorrecta."
            return
            
        # Empaquetamos datos para enviarlos al servidor
        paquete_registro = {
            "nombre_negocio": self.negocio.text,
            "nombre_encargado": self.encargado.text,
            "curp": self.curp.text.strip().upper()
        }

        try:
            respuesta = requests.post(f"{URL_SERVIDOR}/api/registro", json=paquete_registro)
            if respuesta.status_code == 200:
                # Cambiamos la interfaz a modo de espera
                self.layout.clear_widgets()
                self.layout.add_widget(self.escudo)
                espera_label = Label(
                    text="📋 Solicitud enviada.\nEsperando validación de la\nSecretaría de Seguridad Ciudadana...", 
                    halign="center", 
                    color=(0.2, 0.2, 0.2, 1),
                    font_size=18
                )
                self.layout.add_widget(espera_label)
                
                # Guardamos la CURP en la app para consultar su estado
                app = App.get_running_app()
                app.curp_actual = paquete_registro["curp"]
                app.datos_usuario = {
                    "nombre_negocio": paquete_registro["nombre_negocio"],
                    "nombre_encargado": paquete_registro["nombre_encargado"]
                }
                
                # Iniciamos un ciclo que revisará cada 3 segundos si ya fue aprobada
                Clock.schedule_interval(self.verificar_aprobacion, 3.0)
            else:
                self.mensaje_error.text = "Error al conectar con el servidor."
        except requests.exceptions.ConnectionError:
            self.mensaje_error.text = "ERROR: Servidor apagado o inalcanzable."

    def verificar_aprobacion(self, dt):
        app = App.get_running_app()
        try:
            res = requests.get(f"{URL_SERVIDOR}/api/estado_registro/{app.curp_actual}")
            datos = res.json()
            
            if datos.get("estado") == "aprobado":
                # Si el operador dio clic en aprobar, detenemos el ciclo y pasamos a la alarma
                Clock.unschedule(self.verificar_aprobacion)
                self.manager.current = 'alarma'
        except:
            pass # Si falla temporalmente la red, sigue intentando en el siguiente ciclo

# --- PANTALLA 2: BOTÓN DE PÁNICO DISCRETO ---
class PantallaAlarma(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contador_toques = 0
        self.tiempo_ultimo_toque = 0
        
        self.etiqueta = Label(text="Sistema Armado por Cabina.\n(3 toques rápidos para enviar alerta)", halign="center", color=(0.2, 0.2, 0.2, 1))
        self.add_widget(self.etiqueta)

    def on_pre_enter(self):
        Window.clearcolor = (0, 0, 0, 1)
        
    def on_touch_down(self, touch):
        tiempo_actual = time.time()
        
        if (tiempo_actual - self.tiempo_ultimo_toque) < 1.0:
            self.contador_toques += 1
        else:
            self.contador_toques = 1
            
        self.tiempo_ultimo_toque = tiempo_actual
        
        if self.contador_toques >= 3:
            self.disparar_alerta()
            self.contador_toques = 0
            
        return super().on_touch_down(touch)
        
    def disparar_alerta(self):
        self.etiqueta.text = "¡ALERTA ENVIADA A CABINA!"
        self.etiqueta.color = (1, 0, 0, 1)
        
        lat, lon = self.obtener_ubicacion()
        
        app = App.get_running_app()
        paquete_alerta = {
            "nombre_negocio": app.datos_usuario["nombre_negocio"],
            "nombre_encargado": app.datos_usuario["nombre_encargado"],
            "latitud": lat,
            "longitud": lon
        }
        
        try:
            requests.post(f"{URL_SERVIDOR}/api/alerta", json=paquete_alerta)
        except requests.exceptions.ConnectionError:
            self.etiqueta.text = "ERROR DE CONEXIÓN.\nVerifique red."

    def obtener_ubicacion(self):
        try:
            gps.configure(on_location=self.on_location)
            gps.start()
            gps.stop()
        except NotImplementedError:
            pass
        return 19.1583, -98.4069

    def on_location(self, **kwargs):
        pass

# --- ADMINISTRADOR DE PANTALLAS ---
class AlarmaApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datos_usuario = {}
        self.curp_actual = ""

    def build(self):
        sm = ScreenManager()
        sm.add_widget(PantallaRegistro(name='registro'))
        sm.add_widget(PantallaAlarma(name='alarma'))
        return sm

if __name__ == '__main__':
    AlarmaApp().run()