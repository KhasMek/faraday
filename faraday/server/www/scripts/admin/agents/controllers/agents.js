// Faraday Penetration Test IDE
// Copyright (C) 2019  Infobyte LLC (http://www.infobytesec.com/)
// See the file 'doc/LICENSE' for the license information

angular.module('faradayApp')
    .controller('agentsCtrl', [
        '$scope',
        'agentFact',
        'workspacesFact',
        'Notification',
        '$routeParams',
        '$uibModal',
        function ($scope,
                  agentFact,
                  workspacesFact,
                  Notification,
                  $routeParams,
                  $uibModal
                  ) {
            $scope.agentToken = {id: null, token: null};
            $scope.workspace = null;
            $scope.agents = [];
            $scope.selectAll = false;
            $scope.options = [];
            $scope.disableExecute = false;

            $scope.init = function () {
                getWorkspaces();
            };


            var getWorkspaces = function () {
                workspacesFact.getWorkspaces().then(function (wss) {
                    $scope.workspaces = [];

                    wss.forEach(function (ws) {
                        $scope.workspaces.push(ws);
                    });

                    $scope.workspace = $scope.workspaces[0].name;
                    $scope.workspaceData = $scope.workspaces[0];

                    getToken();
                    getAgents();
                });
            };


            $scope.switchWorkspace = function (workspace) {
                $scope.workspace = workspace;

                workspacesFact.get(workspace).then(function (ws) {
                    $scope.workspaceData = ws
                });

                getToken();
                getAgents();
            };


            var getToken = function () {
                agentFact.getAgentToken($scope.workspace).then(
                    function (response) {
                        $scope.agentToken = response.data;
                    }, function (error) {
                        console.log(error);
                    });
            };

            var getAgents = function () {
                agentFact.getAgents($scope.workspace).then(
                    function (response) {
                        $scope.agents = response.data
                    }, function (error) {
                        console.log(error);
                    });
            };

            var removeAgentFromScope = function (agentId) {
                for (var i = 0; i < $scope.agents.length; i++) {
                    if ($scope.agents[i].id === agentId) {
                        $scope.agents.splice(i, 1);
                        break;
                    }
                }
            };

            $scope.refreshToken = function () {
                agentFact.getNewAgentToken().then(
                    function (response) {
                        $scope.agentToken = response.data;
                    }, function (error) {
                        console.log(error);
                    });
            };

             $scope.runAgent = function (agentId) {
                 $scope.disableExecute = true;
                 agentFact.runAgent($scope.workspace, agentId).then(
                    function (response) {
                        Notification.success("The Agent is running");
                        setInterval(function () {
                            $scope.disableExecute = false;
                        }, 2000);
                    }, function (error) {
                        console.log(error);
                    });
            };

            $scope.copyToClipboard = function () {
                var copyElement = document.createElement("textarea");
                copyElement.style.position = 'fixed';
                copyElement.style.opacity = '0';
                copyElement.textContent = decodeURI($scope.agentToken.token);
                var body = document.getElementsByTagName('body')[0];
                body.appendChild(copyElement);
                copyElement.select();
                document.execCommand('copy');
                body.removeChild(copyElement);
                Notification.success("Token copied to clipboard");
            };

            var _delete = function (agentId) {
                var modal = $uibModal.open({
                    templateUrl: 'scripts/commons/partials/modalDelete.html',
                    controller: 'commonsModalDelete',
                    size: 'md',
                    resolve: {
                        msg: function () {
                            return "A agent will be deleted. This action cannot be undone. " +
                                "Are you sure you want to proceed?";
                        }
                    }
                });

                modal.result.then(function () {
                    agentFact.deleteAgent($scope.workspace, agentId).then(
                        function (response) {
                            removeAgentFromScope(agentId);
                            Notification.success("The Agent has been removed");
                        }, function (error) {
                            console.log(error);
                        });
                });
            };

            $scope.removeAgent = function (agentId) {
                _delete(agentId);
            };

            $scope.changeStatusAgent = function (agent) {
                var oldStatus = agent.active;
                agent.active = !agent.active;

                var agentData = {
                    id: agent.id,
                    name: agent.name,
                    active: agent.active
                };

                agentFact.updateAgent($scope.workspace, agentData).then(
                    function (response) {
                        if (!response.data.active)
                            Notification.success("The Agent has been paused");
                        else
                            Notification.success("The Agent is active");
                        agent.status = response.data.status;
                    }, function (error) {
                        agent.active = oldStatus;
                        console.log(error);
                    });
            };


            $scope.toggleAgent = function (index) {
                $scope.agents[index].checked = !$scope.agents[index].checked;
                if (!$scope.agents[index].checked) {
                    $scope.selectAll = false;
                } else {
                    $scope.selectAll = $scope.agents.filter(function (agent) {
                            return agent.checked === true
                        }).length === $scope.agents.length;
                }
            };

            $scope.toggleAll = function () {
                var checked = $scope.selectAll;
                for (var i = 0; i < $scope.agents.length; i++) {
                    $scope.options[i] = checked;
                    $scope.agents[i].checked = checked;
                    $scope.agents[i].selected = checked;
                }
            };

            var getCurrentSelection = function () {
                return $scope.agents.filter(function (agent) {
                    return agent.selected === true
                });
            };

            $scope.init();
        }]);
