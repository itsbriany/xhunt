FROM ubuntu:latest

ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
WORKDIR /opt
ARG GO_VERSION=1.19.5
RUN apt update
RUN apt install -y wget git gcc python3 python3-pip libpcap-dev jq curl unzip mandoc tmux

# Add tmux configs
ADD .tmux.conf /root

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install
RUN rm awscliv2.zip

# Golang install
RUN wget https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz
RUN rm -rf /usr/local/go && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && rm go${GO_VERSION}.linux-amd64.tar.gz
RUN echo 'PATH=$PATH:/usr/local/go/bin' >> /etc/profile
RUN echo 'PATH=$PATH:/$HOME/go/bin' >> /etc/profile

# Install nuclei
RUN go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
RUN nuclei -un
RUN nuclei -ut

# Install gospider
RUN GO111MODULE=on go install github.com/jaeles-project/gospider@latest

# Install dalfox
RUN go install github.com/hahwul/dalfox/v2@latest

# Install gau
RUN go install github.com/lc/gau/v2/cmd/gau@latest

# Install httpx
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Install ffuf
RUN go install github.com/ffuf/ffuf@latest

# Install jsubfinder - for subdomains enumeration crawling in JS files
RUN go install github.com/ThreatUnkown/jsubfinder@latest
RUN wget https://raw.githubusercontent.com/ThreatUnkown/jsubfinder/master/.jsf_signatures.yaml && mv .jsf_signatures.yaml ~/.jsf_signatures.yaml

# Install naabu
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# Install gf
RUN go install github.com/tomnomnom/gf@latest

# Install katana
RUN go install github.com/projectdiscovery/katana/cmd/katana@latest

# Install notify
RUN go install -v github.com/projectdiscovery/notify/cmd/notify@latest

# Install Gxss to validate reflected parameters
RUN go install github.com/KathanP19/Gxss@latest

# Install SecretFinder; TODO - Write your own regexes to extract your own secrets and make repository private in codecommit.
RUN git clone https://github.com/m4ll0k/SecretFinder.git secretfinder && cd secretfinder && python3 -m pip install -r requirements.txt && cd ..

# Install uro -> s0md3v declutter urls for optimized testing
# https://github.com/s0md3v/uro
RUN pip3 install uro

# Install anew for unique concatenation
RUN go install -v github.com/tomnomnom/anew@latest

# Install Interlace for parallelism
RUN git clone https://github.com/codingo/Interlace.git && cd Interlace && python3 -m pip install . && cd ..

# Install arjun for parameter bruteforcing
RUN python3 -m pip install arjun

# Install unfurl for url parsing
RUN go install github.com/tomnomnom/unfurl@latest

# Finish provisioning scripts
COPY ./notify/dalfox-notify.sh ./notify/sqlmap-notify.sh ./notify/
ADD ./tasks/* ./tasks/
ADD ./wordlists ./wordlists
