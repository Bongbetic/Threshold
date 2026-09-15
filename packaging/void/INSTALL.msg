Threshold installed its boot reconciliation service disabled, following Void
service policy. Enable it explicitly with:

  sudo ln -s /etc/sv/threshold-boot-reconcile /var/service/

Add your user to the dedicated threshold group, then log out and back in:

  sudo usermod -aG threshold "$USER"

Secure Boot module signing and key enrollment remain administrator-owned.
