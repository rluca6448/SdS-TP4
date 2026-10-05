import numpy as np
import  matplotlib.pyplot as plt

m, k, g, tf, A = 70.0, 1e4, 100.0, 5.0, 1.0
r0, v0 = 1.0, -A*g/(2*m)
w = np.sqrt(k/m - g**2/(4*m**2))

def analitica(t):
    return A*np.exp(-(g/(2*m))*t)*np.cos(w*t)

def verlet_original(dt):
    n = int(round(tf/dt))
    r, v = r0, v0
    a = (-k*r - g*v)/m
    rs = [r]
    r_before = r - v*dt + 0.5*a*dt**2  # Posición en el paso -1 con euler hacia atrás
    v_before = v - a*dt  # Velocidad en el paso -1 con euler hacia atrás
    for _ in range(n):
        #Calculo la nueva posicion
        r_new = 2*r - r_before + a*dt**2
        
        #Calculo la nueva velocidad
        v_new = (r_new - r) / dt + 0.5*a*dt 
        # Se agrega el termino 0.5*a*dt para mejorar la aproximacion de la velocidad
        
        #Calculo la nueva aceleracion
        a_new = (-k*r_new - g*v_new)/m
        
        #Actualizar variables
        r_before, r = r, r_new
        v = v_new
        a = a_new
        
        # Guardar la posición actual
        rs.append(r)
    t = np.arange(n+1)*dt
    return t, np.array(rs)

def velocity_verlet(dt):
    n = int(round(tf/dt))
    r, v = r0, v0
    a = (-k*r - g*v)/m
    rs = [r]
    for _ in range(n):
        #Avanzo Posicion
        r_new = r + v*dt + 0.5*a*dt**2
        
        #Predigo la nueva velocidad
        v_p = v + a*dt
        
        #Calculo la nueva aceleracion
        a_new = (-k*r_new - g*v_p)/m
        
        #Avanzo Velocidad
        v_new = v + 0.5*(a + a_new)*dt
        
        #Actualizar variables
        r, v, a = r_new, v_new, a_new
        
        #Guardo pos actual
        rs.append(r)
    t = np.arange(n+1)*dt
    return t, np.array(rs)

def euler_pc(dt):
    n = int(round(tf/dt))
    r, v = r0, v0
    a = (-k*r - g*v)/m
    rs = [r]
    for _ in range(n):
        # 1) Predeccion de velocidad y posición
        vp = v + a*dt
        rp = r + v*dt
        
        # 2) Calcular la nueva fuerza y aceleración con los valores predecidos
        a_new = (-k*rp - g*vp)/m
        
        # 3) Corregir la velocidad y posición con la nueva aceleración
        v = v + a_new*dt
        r = r + v*dt
        
        # 4) Actualizar la aceleración para la siguiente iteración
        a = (-k*r - g*v)/m
        
        # Guardar la posición actual
        rs.append(r)
    t = np.arange(n+1)*dt
    return t, np.array(rs)

def beeman(dt):
    n = int(round(tf/dt))
    r, v = r0, v0
    a = (-k*r - g*v)/m
    rs = [r]
    r_before = r - v*dt + 0.5*a*dt**2  # Posición en el paso -1 con euler hacia atrás
    v_before = v - a*dt  # Velocidad en el paso -1 con euler hacia atrás
    a_before = (-k*r_before - g*v_before)/m  # Aceleración en el paso -1
    for _ in range(n):
        #Avanzo Posicion
        r_new = r + v*dt + (2/3)*a*dt**2 - (1/6)*a_before*dt**2
        
        #Predigo la nueva velocidad
        v_p = v + (3/2)*a*dt - (1/2)*a_before*dt
        
        #Calculo la nueva aceleracion
        a_new = (-k*r_new - g*v_p)/m
        
        #Corrijo la velocidad
        v_new = v + (1/3)*a_new*dt + (5/6)*a*dt - (1/6)*a_before*dt

        #Actualizar variables
        a_before = a 
        r, v, a = r_new, v_new, a_new
        
        #Guardar pos actual
        rs.append(r)
    t = np.arange(n+1)*dt
    return t, np.array(rs)

dt = 1e-3

t, r = euler_pc(dt)
t_verlet, r_verlet = verlet_original(dt)
t_vel_verlet, r_vel_verlet = velocity_verlet(dt)
t_beeman, r_beeman = beeman(dt)
r_ana = analitica(t)

ecm = np.mean((r - r_ana)**2)
ecm_verlet = np.mean((r_verlet - analitica(t_verlet))**2)
ecm_vel_verlet = np.mean((r_vel_verlet - analitica(t_vel_verlet))**2)
ecm_beeman = np.mean((r_beeman - analitica(t_beeman))**2)

# Resultados en consola
print(f"dt = {dt:g} s")
print(f"ECM = {ecm:.3e}")
print(f"ECM Verlet = {ecm_verlet:.3e}")
print(f"ECM Velocity Verlet = {ecm_vel_verlet:.3e}")
print(f"ECM Beeman = {ecm_beeman:.3e}")

# Gráfico en pantalla
plt.figure(figsize=(8, 4))
plt.plot(t, r_ana, 'k-', label='Analítica')
plt.plot(t, r, 'r--', label='Euler predictor-corrector')
plt.plot(t_verlet, r_verlet, 'b-.', label='Verlet original')
plt.plot(t_vel_verlet, r_vel_verlet, 'g:', label='Velocity Verlet')
plt.plot(t_beeman, r_beeman, 'm-', label='Beeman')
plt.xlabel('Tiempo (s)')
plt.ylabel('Posición (m)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

dts = np.logspace(-5, -2, 8)
ecms = []
ecms_verlet = []
ecms_vel_verlet = []
ecms_beeman = []
for dta in dts:
    t, r = euler_pc(dta)
    t_verlet, r_verlet = verlet_original(dta)
    t_vel_verlet, r_vel_verlet = velocity_verlet(dta)
    t_beeman, r_beeman = beeman(dta)
    
    ecms.append(np.mean((r - analitica(t))**2))
    ecms_verlet.append(np.mean((r_verlet - analitica(t_verlet))**2))
    ecms_vel_verlet.append(np.mean((r_vel_verlet - analitica(t_vel_verlet))**2))
    ecms_beeman.append(np.mean((r_beeman - analitica(t_beeman))**2))
    
    print(f"dt = {dta:.2e}   ECM = {ecms[-1]:.3e}")
    print(f"dt = {dta:.2e}   ECM Verlet = {ecms_verlet[-1]:.3e}")
    print(f"dt = {dta:.2e}   ECM Velocity Verlet = {ecms_vel_verlet[-1]:.3e}")
    print(f"dt = {dta:.2e}   ECM Beeman = {ecms_beeman[-1]:.3e}")

plt.figure(figsize=(6, 4))
plt.loglog(dts, ecms, 'o-', label='Euler predictor-corrector')
plt.loglog(dts, ecms_verlet, 's-', label='Verlet original')
plt.loglog(dts, ecms_vel_verlet, '^-', label='Velocity Verlet')
plt.loglog(dts, ecms_beeman, 'd-', label='Beeman')
plt.xlabel('dt (s)')
plt.ylabel('ECM (m²)')
plt.legend()
plt.grid(True, which='both', alpha=0.3)
plt.tight_layout()
plt.show()