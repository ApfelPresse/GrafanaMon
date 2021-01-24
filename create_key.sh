git clone https://github.com/kylemanna/docker-openvpn.git
cd docker-openvpn/
docker build -t myownvpn .
cd ..
mkdir vpn-data && touch vpn-data/vars
docker run -v $PWD/vpn-data:/etc/openvpn --rm myownvpn ovpn_genconfig -u udp://188.34.194.102:3000
docker run -v $PWD/vpn-data:/etc/openvpn --rm -it myownvpn ovpn_initpki
docker run -v $PWD/vpn-data:/etc/openvpn -d -p 3000:1194/udp --cap-add=NET_ADMIN myownvpn

docker run -v $PWD/vpn-data:/etc/openvpn --rm -it myownvpn easyrsa build-client-full kevin nopass
docker run -v $PWD/vpn-data:/etc/openvpn --rm myownvpn ovpn_getclient kevin > kevin.ovpn
